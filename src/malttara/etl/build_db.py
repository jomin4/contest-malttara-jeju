"""원본(data/raw/) → data/db/malttara.sqlite, data/db/map.json (개발 PC 전용 ETL).

순서: 경계 → 1349 정제 → 분류 매칭(TourAPI·811·812·784·858) → TourAPI 음식점·카페 추가
      → 563 읍면동 집계 → 1208 반경 집계 → 189/190 입장객 → data_sources·meta → map.json
없는 원본(특히 TourAPI 스냅샷)은 그 단계만 건너뛰고 로그를 남긴다.

실행: PYTHONPATH=src python -m malttara.etl.build_db [--raw data/raw] [--db data/db/malttara.sqlite] [--map data/db/map.json]
563 원본이 약 2.4GB라 수 분 걸린다.
"""
import argparse
import csv
import datetime
import glob
import json
import os
import re
import sys

from malttara.config import ROOT, load_config
from malttara.db import connect, meta_set
from malttara.geo import haversine_km
from malttara.etl.boundaries import ATTRIBUTION, build_map, find_boundary_file, load_polygons, nearest_emd
from malttara.etl.categorize import _keyword_category, _match_prepared, _prepare, categorize_places
from malttara.etl.clean_places import assign_region, clean_1349, emd_of_point
from malttara.etl.emd_stats import aggregate_563
from malttara.etl.names import load_mapping, normalize_name, open_csv, read_csv_rows
from malttara.etl.quiet import quiet_counts, read_1208_points
from malttara.etl.sights import aggregate_sights, match_sights

MAPPING_DIR = os.path.join(str(ROOT), "data", "mapping")
MAP_TOLERANCE = 0.4            # map.json 단순화 허용 오차(view_box 단위)
NEAREST_EMD_MAX_KM = 1.5       # 경계 밖 좌표를 가장 가까운 읍면동으로 붙이는 최대 거리
HUB_URL = "https://jejudatahub.net/data/view/data/{}"
SOURCE_NAMES = {
    "1349": "제주관광공사 제주관광정보시스템(VISIT JEJU) 여행장소",
    "563": "내국인 유동인구 구성비율",
    "1208": "월별 렌터카 체류 거점 위치 정보(2021년 하반기)",
    "189": "제주특별자치도 내국인 관광지 입장객 수 추이",
    "190": "제주특별자치도 외국인 관광지 입장객 수 추이",
    "784": "제주특별자치도 해수욕장 정보",
    "858": "무장애 여행지 정보 통합",
    "811": "오름 위치 정보(허브 Open API)",
    "812": "박물관 및 미술관 위치 정보(허브 Open API)",
}
# 784 해변명은 "협재"처럼 접미어가 없다. 1349 이름과 맞추려고 접미어를 붙인 이름을 참조로 쓴다.
BEACH_SUFFIXES = ["해수욕장", "해변"]
# TourAPI 스냅샷에서 places에 추가하는 유형: 음식점(카페 포함)
TOURAPI_ADD_CONTENT_TYPES = {"39", "음식점"}   # 스냅샷은 유형 이름("음식점")으로 저장된다


def _csvs(raw_dir: str, sub: str) -> list:
    return sorted(glob.glob(os.path.join(raw_dir, sub, "*.csv")))


def _ym_range(values) -> "str | None":
    """숫자만 남겨 앞 6자리(YYYYMM) 최소~최대 → 'YYYY-MM~YYYY-MM'."""
    yms = set()
    for v in values:
        d = re.sub(r"\D", "", str(v or ""))
        if len(d) >= 6 and 1 <= int(d[4:6]) <= 12:
            yms.add(d[:6])
    if not yms:
        return None
    lo, hi = min(yms), max(yms)
    return f"{lo[:4]}-{lo[4:]}~{hi[:4]}-{hi[4:]}"


def _load_json(path: str) -> "list | None":
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _is_island_emd(emd: str, etl_cfg: dict) -> bool:
    return any(emd.endswith(tok) for tok in etl_cfg.get("island_address_tokens", []))


def _mtime_date(path: str) -> str:
    return datetime.date.fromtimestamp(os.path.getmtime(path)).isoformat()


def _tourapi_places(items: list, existing: list, etl_cfg: dict, regions_cfg: dict, alias: dict, polygons) -> list:
    """TourAPI 음식점(카페 포함) → places 행. 1349와 같은 정제 규칙, 1349에 같은 장소가 있으면 뺀다."""
    picked = [it for it in items if str(it.get("content_type")) in TOURAPI_ADD_CONTENT_TYPES]
    rows = [{"장소명": it.get("name") or "", "지번주소": it.get("addr") or "",
             "위도": it.get("lat"), "경도": it.get("lon")} for it in picked]
    cleaned = clean_1349(rows, etl_cfg, regions_cfg, alias, polygons=polygons)
    prefixes = etl_cfg.get("name_prefixes", [])
    dedup_km = etl_cfg.get("dedup_max_m", 50) / 1000.0
    by_key = {}
    for p in existing:
        by_key.setdefault(normalize_name(p["name"], prefixes), []).append((p["lat"], p["lon"]))
    out = []
    for c in cleaned:
        it = picked[int(c["place_id"].split("-")[1]) - 1]
        key = normalize_name(c["name"], prefixes)
        if any(haversine_km(c["lat"], c["lon"], a, b) <= dedup_km for a, b in by_key.get(key, [])):
            continue
        c.update({
            "place_id": f"ptour-{it['content_id']}",
            "source": "tourapi",
            "category": it.get("category"),
            "category_source": "tourapi",
            "overview": it.get("overview"),
        })
        out.append(c)
    return out


def _fix_outside_emd(places: list, polygons: list, regions_cfg: dict) -> "tuple[int, int]":
    """경계 밖 좌표(해변·포구처럼 단순화된 해안선 바깥)는 지번주소 대신 1km 이내 가장 가까운 읍면동을 쓴다.

    지번주소 폴백은 법정동(예: '서귀포시 색달동')이나 틀린 주소를 내서 행정동 키와 맞지 않는다.
    반환: (가장 가까운 경계로 정한 곳, 그래도 지번주소에 남은 곳)
    """
    near = by_addr = 0
    for p in places:
        if emd_of_point(p["lat"], p["lon"], polygons) is not None:
            continue
        emd = nearest_emd(p["lat"], p["lon"], polygons, NEAREST_EMD_MAX_KM)
        if emd is not None:
            p["emd"], p["region_id"] = emd, assign_region(emd, regions_cfg)
            near += 1
        else:
            by_addr += 1
    return near, by_addr


def build_db(raw_dir: str, out_db: str, out_map: str, log=print, mapping_dir: str = MAPPING_DIR) -> dict:
    """원본 → SQLite + map.json. 단계별 건수 dict를 돌려준다(콘솔 출력용)."""
    etl_cfg, regions_cfg, settings = load_config("etl"), load_config("regions"), load_config("settings")
    alias = load_mapping(os.path.join(mapping_dir, "emd_alias.csv"), "raw", "emd")
    manual_sights = load_mapping(os.path.join(mapping_dir, "sights_to_places.csv"), "sight_name", "place_id")
    prefixes = etl_cfg.get("name_prefixes", [])
    today = datetime.date.today().isoformat()
    stats = {"skipped": []}
    sources = {}  # source_id → data_sources 행

    def src(sid, **kw):
        row = {"source_id": sid, "name": SOURCE_NAMES.get(sid, sid), "url": HUB_URL.format(sid) if sid.isdigit() else None,
               "fetched_at": None, "period_actual": None, "rows": None, "license": None, "notes": None}
        row.update(kw)
        sources[sid] = row

    def skip(name, why):
        stats["skipped"].append(name)
        log(f"[건너뜀] {name}: {why}")

    # 0) 경계
    boundary = find_boundary_file(raw_dir)
    polygons = load_polygons(boundary, alias) if boundary else None
    if polygons:
        log(f"[경계] {os.path.basename(boundary)}: 제주 읍면동 {len(polygons)}개")
        src("boundary", name="SGIS 행정동 경계(가공: vuski/admdongkor ver20261001)",
            url="https://github.com/vuski/admdongkor", fetched_at=_mtime_date(boundary), rows=len(polygons),
            license="CC BY 4.0 (원자료 공공누리 1유형)", notes=ATTRIBUTION)
    else:
        skip("boundary", "경계 파일 없음 → 읍면동은 지번주소로 판정, map.json 생략")
    stats["boundary_emds"] = len(polygons or [])

    # 1) 1349 정제
    rows = [r for p in _csvs(raw_dir, "1349") for r in read_csv_rows(p)]
    places = clean_1349(rows, etl_cfg, regions_cfg, alias, polygons=polygons)
    for p in places:
        p.setdefault("quiet_count", None)
    stats["1349_rows"] = len(rows)
    if polygons:
        near, by_addr = _fix_outside_emd(places, polygons, regions_cfg)
        stats["places_emd_nearest"] = near
        stats["places_emd_by_address"] = by_addr
    # 주소가 틀려 is_island를 빠져나간 부속섬 좌표(예: 주소 '성산읍', 좌표 우도)는 읍면동으로 한 번 더 거른다
    before = len(places)
    places = [p for p in places if not (p["emd"] and _is_island_emd(p["emd"], etl_cfg))]
    stats["places_island_emd_dropped"] = before - len(places)
    stats["places_1349"] = len(places)
    log(f"[1349] 원본 {len(rows)}행 → 정제 후 {len(places)}곳")
    src("1349", rows=len(rows), fetched_at=_mtime_date(_csvs(raw_dir, "1349")[0]) if rows else None,
        notes=f"정제 후 {len(places)}곳(본섬 범위·부속섬·비장소 제외, 50m 내 같은 이름 중복 제거)")

    # 2) 분류 참조 세트
    ref_sets = []
    tour = _load_json(os.path.join(raw_dir, "tourapi_jeju.json"))
    if tour is None:
        skip("tourapi", "tourapi_jeju.json 없음(DATA_GO_KR_KEY 미발급)")
    else:
        ref_sets.append(("tourapi", tour))
    for sid in ("811", "812"):
        path = os.path.join(raw_dir, f"hub_{sid}.json")
        refs = _load_json(path)
        if refs is None:
            skip(f"hub_{sid}", f"hub_{sid}.json 없음")
            continue
        ref_sets.append((f"hub_{sid}", refs))
        src(sid, rows=len(refs), fetched_at=_mtime_date(path))
    beach_rows = [r for p in _csvs(raw_dir, "784") for r in read_csv_rows(p)]
    if beach_rows:
        names = sorted({(r.get("해변명") or "").strip() for r in beach_rows} - {""})
        refs = [{"name": n + suf, "lat": None, "lon": None, "category": "해수욕장"} for n in names for suf in BEACH_SUFFIXES]
        ref_sets.append(("hub_784", refs))
        years = sorted({(r.get("기준일(년)") or "").strip() for r in beach_rows} - {""})
        src("784", rows=len(beach_rows), period_actual=f"{years[0]}~{years[-1]}" if years else None,
            fetched_at=_mtime_date(_csvs(raw_dir, "784")[0]), notes=f"해변 {len(names)}곳(좌표 없음, 이름+'해수욕장'/'해변' 일치만)")
    else:
        skip("hub_784", "784 CSV 없음")
    bf_rows = [r for p in _csvs(raw_dir, "858") for r in read_csv_rows(p)]
    if bf_rows:
        all_858 = [{"name": (r.get("장소명") or "").strip(), "lat": r.get("위도"), "lon": r.get("경도")} for r in bf_rows]
        # 858은 '무장애 여행지'라 분류로 쓰지 않는다. 이름 키워드로 분류가 정해지는 참조만 남긴다.
        refs = []
        for r in all_858:
            cat = _keyword_category(r["name"], etl_cfg.get("keyword_categories", {}))
            if cat:
                refs.append(dict(r, category=cat))
        ref_sets.append(("hub_858", refs))
        src("858", rows=len(bf_rows), fetched_at=_mtime_date(_csvs(raw_dir, "858")[0]))
    else:
        all_858 = []
        skip("hub_858", "858 CSV 없음")

    cat_counts = categorize_places(places, ref_sets, etl_cfg)
    stats["category_counts"] = cat_counts
    log(f"[분류] {cat_counts}")
    for sid in ("811", "812"):
        if sid in sources:
            sources[sid]["notes"] = f"1349 정제 장소 {len(places)}곳 중 분류 매칭 {cat_counts.get('hub_' + sid, 0)}곳"
    if "784" in sources:
        sources["784"]["notes"] += f"; 분류 매칭 {cat_counts.get('hub_784', 0)}곳"
    if all_858:
        prep = _prepare(all_858, prefixes)
        n858 = sum(1 for p in places if _match_prepared(p, prep, etl_cfg["match"], prefixes))
        stats["858_matched_any"] = n858
        sources["858"]["notes"] = (f"이름·좌표 검증용: 858 {len(all_858)}곳 중 1349 정제 장소와 일치 {n858}곳, "
                                   f"그중 키워드 분류로 쓴 곳 {cat_counts.get('hub_858', 0)}곳")

    # 3) TourAPI 음식점·카페 추가
    added = []
    if tour is not None:
        added = _tourapi_places(tour, places, etl_cfg, regions_cfg, alias, polygons)
        if polygons:
            _fix_outside_emd(added, polygons, regions_cfg)
        added = [p for p in added if not (p["emd"] and _is_island_emd(p["emd"], etl_cfg))]
        for p in added:
            p["quiet_count"] = None
        places.extend(added)
        src("tourapi", name="한국관광공사 국문 관광정보 서비스(KorService2)",
            url="https://www.data.go.kr/data/15101578/openapi.do", rows=len(tour),
            fetched_at=_mtime_date(os.path.join(raw_dir, "tourapi_jeju.json")),
            notes=f"분류 매칭 {cat_counts.get('tourapi', 0)}곳, 음식점·카페 {len(added)}곳 추가")
    stats["places_tourapi_added"] = len(added)
    log(f"[TourAPI] 음식점·카페 추가 {len(added)}곳")

    if stats.get("places_emd_nearest") is not None:
        log(f"[읍면동] 경계 밖 좌표 → 가장 가까운 경계 {stats['places_emd_nearest']}곳, "
            f"지번주소 폴백 {stats['places_emd_by_address']}곳, 부속섬 좌표 제외 {stats['places_island_emd_dropped']}곳")

    # 4) 563 읍면동 집계(부속섬 읍면동 제외)
    emd_rows = []
    f563 = _csvs(raw_dir, "563")
    if f563:
        info = {}
        log(f"[563] {os.path.basename(f563[0])} 집계 중(큰 파일은 수 분)...")
        emd_rows = [r for r in aggregate_563(f563[0], alias, info) if not _is_island_emd(r["emd"], etl_cfg)]
        period = emd_rows[0]["period"] if emd_rows else None
        emds = sorted({r["emd"] for r in emd_rows})
        no_region = [e for e in emds if assign_region(e, regions_cfg) is None]
        src("563", rows=info.get("rows"), period_actual=period, fetched_at=_mtime_date(f563[0]),
            notes=f"본섬 읍면동 {len(emds)}개(우도면·추자면 제외) × 월 1~12 + 전체 평균")
        if no_region:
            log(f"[563] 권역을 못 정한 읍면동: {no_region}")
        if polygons:
            bnames = {e for e, _ in polygons}
            miss = [e for e in emds if e not in bnames]
            if miss:
                log(f"[563] 경계에 없는 읍면동 키(emd_alias.csv 확인): {miss}")
            stats["563_emds_not_in_boundary"] = miss
        log(f"[563] 원본 {info.get('rows')}행, 기간 {period}, 읍면동 {len(emds)}개")
    else:
        skip("563", "563 CSV 없음")
    stats["emds_with_stats"] = len({r["emd"] for r in emd_rows})
    emd_set = {r["emd"] for r in emd_rows}
    stats["places_with_emd_stats"] = sum(1 for p in places if p["emd"] in emd_set)

    # 5) 1208 반경 집계
    f1208 = _csvs(raw_dir, "1208")
    if f1208:
        points = list(read_1208_points(f1208))
        qc = quiet_counts(places, points, settings["quiet_radius_km"])
        for p in places:
            p["quiet_count"] = qc.get(p["place_id"])
        dts = []
        for path in f1208:
            with open_csv(path) as f:
                dts.extend(r.get("collection_dt") for r in csv.DictReader(f))
        src("1208", rows=len(points), period_actual=_ym_range(dts), fetched_at=_mtime_date(f1208[0]),
            notes=f"파일 {len(f1208)}개; 반경 {settings['quiet_radius_km']}km 체류 거점 수를 장소 {len(qc)}곳에 기록")
        stats["1208_points"] = len(points)
        log(f"[1208] 체류 거점 {len(points)}개 → quiet_count {len(qc)}곳")
    else:
        skip("1208", "1208 CSV 없음")
    stats["places_with_quiet"] = sum(1 for p in places if p.get("quiet_count") is not None)

    # 6) 189/190 입장객
    sight_paths = {}
    sight_names = set()
    for kind, sid in (("domestic", "189"), ("foreign", "190")):
        files = _csvs(raw_dir, sid)
        if not files:
            skip(sid, f"{sid} CSV 없음")
            continue
        sight_paths[kind] = files[0]
        srows = read_csv_rows(files[0])
        names = {(r.get("관광지명") or "").strip() for r in srows} - {""}
        sight_names |= names
        src(sid, rows=len(srows), period_actual=_ym_range(r.get("날짜") for r in srows),
            fetched_at=_mtime_date(files[0]), notes=f"관광지 {len(names)}곳")
    visits, mapping = [], {}
    if sight_paths:
        valid_ids = {p["place_id"] for p in places}
        manual = {k: v for k, v in manual_sights.items() if v in valid_ids}
        bad = sorted(set(manual_sights) - set(manual))
        if bad:
            log(f"[189/190] 수작업표의 place_id가 장소 목록에 없음: {bad}")
        mapping = match_sights(sorted(sight_names), places, manual, prefixes)
        visits = aggregate_sights(sight_paths, mapping)
        note = f"관광지 {len(sight_names)}곳 중 장소 매칭 {len(mapping)}곳(수작업 {len(manual)}곳 포함)"
        for sid in ("189", "190"):
            if sid in sources:
                sources[sid]["notes"] += "; " + note
        log(f"[189/190] {note}, 월별 행 {len(visits)}개")
    stats["sight_names"] = len(sight_names)
    stats["sights_matched"] = len(mapping)
    stats["sight_visit_rows"] = len(visits)

    # 7) 쓰기
    if os.path.exists(out_db):
        os.remove(out_db)
    os.makedirs(os.path.dirname(os.path.abspath(out_db)), exist_ok=True)
    conn = connect(out_db)
    try:
        conn.executemany("INSERT INTO regions(region_id, name) VALUES (?, ?)",
                         [(r["region_id"], r["name"]) for r in regions_cfg["regions"]])
        cols = ("place_id", "name", "lat", "lon", "emd", "region_id", "category", "category_source",
                "overview", "source", "quiet_count", "in_scope")
        conn.executemany(f"INSERT INTO places({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})",
                         [tuple(p.get(c) for c in cols) for p in places])
        conn.executemany(
            "INSERT INTO emd_stats(emd, month, visit_pop, resident_pop, visit_ratio, period, source_id) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            [(r["emd"], r["month"], r["visit_pop"], r["resident_pop"], r["visit_ratio"], r["period"], r["source_id"])
             for r in emd_rows])
        conn.executemany(
            "INSERT INTO sight_visits(place_id, year_month, domestic, foreign_, source_id) VALUES (?, ?, ?, ?, ?)",
            [(v["place_id"], v["year_month"], v["domestic"], v["foreign"], v["source_id"]) for v in visits])
        dcols = ("source_id", "name", "url", "fetched_at", "period_actual", "rows", "license", "notes")
        conn.executemany(f"INSERT INTO data_sources({', '.join(dcols)}) VALUES ({', '.join('?' for _ in dcols)})",
                         [tuple(s[c] for c in dcols) for s in sources.values()])
        meta_set(conn, "data_version", today)
        meta_set(conn, "build_stats", json.dumps(stats, ensure_ascii=False))
        conn.commit()
    finally:
        conn.close()
    stats["places"] = len(places)
    stats["places_no_region"] = sum(1 for p in places if not p.get("region_id"))
    stats["places_by_region"] = {r["region_id"]: sum(1 for p in places if p.get("region_id") == r["region_id"])
                                 for r in regions_cfg["regions"]}

    # 8) map.json
    if boundary:
        m = build_map(boundary, regions_cfg, alias, out_map, MAP_TOLERANCE)
        stats["map_emds"] = len(m["emds"])
        log(f"[지도] 읍면동 {len(m['emds'])}개, view_box {m['view_box']}")
    else:
        stats["map_emds"] = 0
    return stats


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description="원본 → data/db/malttara.sqlite, data/db/map.json")
    ap.add_argument("--raw", default=os.path.join(str(ROOT), "data", "raw"))
    ap.add_argument("--db", default=os.path.join(str(ROOT), "data", "db", "malttara.sqlite"))
    ap.add_argument("--map", default=os.path.join(str(ROOT), "data", "db", "map.json"))
    args = ap.parse_args(argv)
    stats = build_db(args.raw, args.db, args.map)
    print("== 단계별 건수 ==")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print(f"저장: {args.db}, {args.map}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
