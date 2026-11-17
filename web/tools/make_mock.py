"""목업 픽스처 생성 (B 트랙 개발용). 장소명·수치는 모두 모의 값."""
import json, math, hashlib, sys
from shapely.geometry import shape, Polygon, MultiPolygon, box, Point, mapping
from shapely.ops import unary_union

SRC, OUT = sys.argv[1], sys.argv[2]
ISLAND_EMDS = {"제주시 추자면", "제주시 우도면"}
REGIONS = [("city", "제주시내권"), ("west", "서부권"), ("east", "동부권"), ("south", "중문·서귀포권")]  # 계약: 4권역 확정
WEST = {"제주시 애월읍", "제주시 한림읍", "제주시 한경면", "서귀포시 대정읍", "서귀포시 안덕면"}
EAST = {"제주시 조천읍", "제주시 구좌읍", "서귀포시 성산읍", "서귀포시 표선면"}
MOUNTAIN_BOX = box(126.47, 33.32, 126.60, 33.40)  # 목업용 박스

def region_of(emd):
    if emd in WEST: return "west"
    if emd in EAST: return "east"
    if emd == "서귀포시 남원읍" or (emd.startswith("서귀포시") and emd.endswith("동")): return "south"
    if emd.startswith("제주시") and emd.endswith("동"): return "city"
    return None

def h(s, lo=0.0, hi=1.0):
    v = int(hashlib.md5(s.encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
    return lo + (hi - lo) * v

fc = json.load(open(SRC, encoding="utf-8"))
emds = []
for f in fc["features"]:
    emd = f["properties"]["adm_nm"].replace("제주특별자치도 ", "")
    if emd in ISLAND_EMDS: continue
    g = shape(f["geometry"])
    parts = list(g.geoms) if isinstance(g, MultiPolygon) else [g]
    big = max(p.area for p in parts)
    parts = [p for p in parts if p.area >= big * 0.05]   # 비양도·가파도·마라도 등 작은 섬 제외
    g = MultiPolygon(parts) if len(parts) > 1 else parts[0]
    emds.append((emd, region_of(emd), g))

allg = unary_union([g for _, _, g in emds])
min_lon, min_lat, max_lon, max_lat = allg.bounds
pad = 0.01
min_lon -= pad; max_lon += pad; min_lat -= pad; max_lat += pad
COS = math.cos(math.radians(33.4))
W = 1000.0
scale = W / ((max_lon - min_lon) * COS)
H = (max_lat - min_lat) * scale

def proj(lon, lat):
    return ((lon - min_lon) * scale * COS, (max_lat - lat) * scale)

def to_d(g, tol=0.0012):
    g = g.simplify(tol, preserve_topology=True)
    polys = list(g.geoms) if hasattr(g, "geoms") else [g]
    out = []
    for p in polys:
        for ring in [p.exterior, *p.interiors]:
            pts = [proj(x, y) for x, y in ring.coords]
            out.append("M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in pts) + "Z")
    return "".join(out)

map_json = {
    "view_box": f"0 0 {W:.0f} {H:.0f}",
    "emds": [{"emd": e, "region_id": r, "d": to_d(g)} for e, r, g in emds],
    "regions": [],
    "project": {"min_lon": round(min_lon, 6), "max_lat": round(max_lat, 6), "scale": round(scale, 4)},
    "_mock": True,
    "attribution": "목업 · 통계청 SGIS 행정동 경계(공공누리 제1유형) 가공: vuski/admdongkor, CC BY 4.0",
}
for rid, name in REGIONS:
    if True:
        g = unary_union([gg for _, r, gg in emds if r == rid]).buffer(0.0004).buffer(-0.0004)
    map_json["regions"].append({"region_id": rid, "name": name, "d": to_d(g, 0.002)})

# 통계 (모의)
stats = {}
for m in range(0, 13):
    vals = []
    for e, r, _ in emds:
        vr = round(h(f"{e}-{m}", 0.4, 6.0) * (1.25 if m in (7, 8) else 1.0), 2)
        vals.append({"emd": e, "region_id": r, "visit_ratio": vr})
    vals.sort(key=lambda x: x["visit_ratio"])
    n = len(vals)
    for i, v in enumerate(vals):
        v["pct"] = round(i / (n - 1), 2)
    missing = {"제주시 도두동"}  # 지표 없음 표시 확인용
    for v in vals:
        if v["emd"] in missing: v["visit_ratio"] = None; v["pct"] = None
    stats[str(m)] = {"period": "2018-01~2022-09", "source_id": "563", "month": None if m == 0 else m,
                     "items": sorted(vals, key=lambda x: x["emd"])}

# 장소 (모의)
CATS = ["해수욕장", "오름", "숲길", "박물관", "음식점", "카페", "체험", "해변"]
LABEL = {"해수욕장": "해변", "해변": "해안", "오름": "오름", "숲길": "숲길", "박물관": "전시관", "음식점": "식당", "카페": "카페", "체험": "체험장"}
places = {}
emd_by_region = {}
for e, r, g in emds:
    emd_by_region.setdefault(r, []).append((e, g))
for rid, name in REGIONS:
    for i in range(8):
        cat = CATS[i]
        lst = emd_by_region[rid]; emd, gx = lst[i % len(lst)]
        minx, miny, maxx, maxy = gx.bounds
        k = 0
        while True:
            pt = Point(h(f"{rid}{i}{k}x", minx, maxx), h(f"{rid}{i}{k}y", miny, maxy)); k += 1
            if gx.contains(pt): break
        pid = f"p-mock-{rid}-{i+1:02d}"
        st = next((x for x in stats["0"]["items"] if x["emd"] == emd), None)
        nearby_missing = (i == 6)
        qc = None if nearby_missing else int(h(pid + "q", 20, 900))
        places[pid] = {
            "place_id": pid, "name": f"모의 {LABEL[cat]} {name.replace('권', '')[:2]}{i+1}", "lat": round(pt.y, 6), "lon": round(pt.x, 6),
            "emd": emd, "region_id": rid, "region_name": name,
            "category": None if i == 7 and rid == "east" else cat,
            "category_source": "none" if i == 7 and rid == "east" else ("tourapi" if i % 3 else "hub_811"),
            "overview": None if i % 4 == 3 else "목업 개요 문장입니다. 실제 서버 연결 후 TourAPI 개요가 들어갑니다. 화면 줄바꿈과 세 줄 말줄임을 확인하기 위한 긴 문장입니다.",
            "source": "tourapi" if cat in ("음식점", "카페") else "1349",
            "score": round(h(pid + "s", 0.3, 0.95), 2), "interest": 1.0, "spread": round(1 - (st["pct"] or 0.5), 2), "quiet": round(h(pid + "qq"), 2),
            "indicators": {
                "region": {"emd": emd, "visit_ratio": st["visit_ratio"], "pct": st["pct"], "period": "2018-01~2022-09", "month": None,
                           "source_id": "563", "missing": st["visit_ratio"] is None},
                "nearby": {"quiet_count": qc, "pct": None if nearby_missing else round(h(pid + "p"), 2), "radius_km": 1.0,
                           "period": "2021-07~12 토요일", "source_id": "1208", "missing": nearby_missing},
            },
            "has_trend": i in (0, 3),
        }

trend = {}
for pid, p in places.items():
    if not p["has_trend"]: continue
    series = []
    for y in (2023, 2024):
        for mth in range(1, 13):
            base = h(pid, 20000, 90000)
            season = 1 + 0.35 * math.sin((mth - 4) / 12 * 2 * math.pi)
            series.append({"year_month": f"{y}-{mth:02d}", "domestic": int(base * season * h(f"{pid}{y}{mth}", 0.9, 1.1)),
                           "foreign": None if (y == 2023 and mth < 4) else int(base * 0.12 * season * h(f"{pid}f{y}{mth}", 0.8, 1.2))})
    trend[pid] = {"place_id": pid, "period": "2023-01~2024-12", "source_ids": ["189", "190"], "series": series}

config = {
    "interests": [{"key": k, "slot": k in ("음식", "카페")} for k in ["바다", "오름", "숲", "실내·전시", "체험·레저", "음식", "카페"]],
    "regions": [{"region_id": r, "name": n} for r, n in REGIONS],
    "max_days": 7,
}
json.dump(map_json, open(f"{OUT}/map.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
json.dump(stats, open(f"{OUT}/stats_emd.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
json.dump(places, open(f"{OUT}/places.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
json.dump(trend, open(f"{OUT}/trend.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
json.dump(config, open(f"{OUT}/config.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print("view_box", map_json["view_box"], "emds", len(map_json["emds"]), "places", len(places))
