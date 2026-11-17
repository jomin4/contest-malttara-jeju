"""원본 없이 Tool·서버를 개발·시험하기 위한 결정론적 모의 DB.

실행 중(`run.py --mock`)에도 import하므로 표준 라이브러리만 쓴다.
장소 이름은 실제 장소처럼 보이지 않게 "모의 …"로 짓는다.
"""
import os

from malttara.config import load_config
from malttara.db import connect, meta_set

# 권역별 (중심 위도, 중심 경도, 읍면동 2개, 방문/거주 비율 기준값)
REGION_SPECS = {
    "city": (33.500, 126.530, ["제주시 일도1동", "제주시 용담2동"], 3.0),
    "west": (33.420, 126.300, ["제주시 애월읍", "제주시 한림읍"], 1.6),
    "east": (33.480, 126.850, ["제주시 구좌읍", "서귀포시 성산읍"], 2.2),
    "south": (33.260, 126.560, ["서귀포시 서홍동", "서귀포시 남원읍"], 1.1),
}
CATEGORIES = ["해수욕장", "오름", "숲", "박물관", "음식점", "카페", "해수욕장", "포구"]
CATEGORY_LABEL = {"해수욕장": "해변", "오름": "오름", "숲": "숲길", "박물관": "박물관",
                  "음식점": "식당", "카페": "카페", "포구": "포구"}
MISSING_EMD = "제주시 한경면"   # emd_stats에 없는 읍면동(지표 없음 시험용)
# 한적함 요청이 순위를 바꾸는 장면: 붐비는 시내 해변 vs 한적한 남부 숲
QUIET_OVERRIDES = {"p-mock-city-00": 490, "p-mock-city-06": 495, "p-mock-south-02": 1}


def _places():
    out = []
    for r_idx, (rid, (lat0, lon0, emds, _)) in enumerate(REGION_SPECS.items()):
        for i, cat in enumerate(CATEGORIES):
            emd = emds[i % 2]
            if rid == "west" and i == 7:
                emd = MISSING_EMD
            pid = f"p-mock-{rid}-{i:02d}"
            quiet = None if i == 5 else QUIET_OVERRIDES.get(pid, (i * 97 + r_idx * 31) % 500)
            out.append({
                "place_id": pid,
                "name": f"모의 {CATEGORY_LABEL[cat]} {rid}-{i:02d}",
                "lat": round(lat0 + 0.01 * (i % 3), 6),
                "lon": round(lon0 + 0.012 * (i // 3), 6),
                "emd": emd,
                "region_id": rid,
                "category": cat,
                "category_source": "keyword" if cat in ("오름", "해수욕장") else "tourapi",
                "overview": None if i % 4 == 3 else f"모의 개요 {rid}-{i:02d}",
                "source": "tourapi" if cat in ("음식점", "카페") else "1349",
                "quiet_count": quiet,
                "in_scope": 1,
            })
    return out


def build_mock_map(path: str) -> dict:
    """모의 읍면동을 사각형으로 그린 지도(계약 GET /api/map 모양). 실제 경계가 아니다."""
    import json
    import math
    min_lon, max_lat, scale = 126.10, 33.60, 1000.0
    kx = scale * math.cos(math.radians(33.4))

    def xy(lat, lon):
        return round((lon - min_lon) * kx, 1), round((max_lat - lat) * scale, 1)

    def rect(lat1, lon1, lat2, lon2):
        pts = [xy(lat1, lon1), xy(lat1, lon2), xy(lat2, lon2), xy(lat2, lon1)]
        return "M" + " L".join(f"{x} {y}" for x, y in pts) + " Z"

    emds, regions = [], []
    for rid, (lat0, lon0, names, _) in REGION_SPECS.items():
        boxes = []
        for j, emd in enumerate(names + ([MISSING_EMD] if rid == "west" else [])):
            box = (lat0 - 0.01, lon0 - 0.01 + 0.04 * j, lat0 + 0.04, lon0 + 0.03 + 0.04 * j)
            boxes.append(box)
            emds.append({"emd": emd, "region_id": rid, "d": rect(*box)})
        regions.append({"region_id": rid, "name": next(r["name"] for r in load_config("regions")["regions"]
                                                       if r["region_id"] == rid),
                        "d": rect(min(b[0] for b in boxes), min(b[1] for b in boxes),
                                  max(b[2] for b in boxes), max(b[3] for b in boxes))})
    w, h = xy(33.10, 127.00)
    out = {"view_box": f"0 0 {w} {h}", "emds": emds, "regions": regions,
           "project": {"min_lon": min_lon, "max_lat": max_lat, "scale": scale},
           "attribution": "모의 지도(실제 경계 아님)"}
    with open(path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False)
    return out


def build_mock_db(path: str) -> None:
    if os.path.exists(path):
        os.remove(path)
    conn = connect(path)
    regions = load_config("regions")["regions"]
    conn.executemany("INSERT INTO regions(region_id, name) VALUES (?, ?)",
                     [(r["region_id"], r["name"]) for r in regions])
    places = _places()
    cols = list(places[0].keys())
    conn.executemany(
        f"INSERT INTO places({', '.join(cols)}) VALUES ({', '.join('?' for _ in cols)})",
        [tuple(p[c] for c in cols) for p in places],
    )
    stats = []
    for rid, (_, _, emds, base) in REGION_SPECS.items():
        for j, emd in enumerate(emds):
            for month, factor in ((0, 1.0), (11, 0.8)):
                resident = 20000.0 + 5000 * j
                ratio = round(base * factor + 0.4 * j, 4)
                stats.append((emd, month, resident * ratio, resident, ratio, "2018-01~2022-09", "563"))
    conn.executemany(
        "INSERT INTO emd_stats(emd, month, visit_pop, resident_pop, visit_ratio, period, source_id) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)", stats)
    visits = []
    for pid, base in (("p-mock-city-03", 30000), ("p-mock-east-01", 12000)):
        for k, ym in enumerate(("2024-01", "2024-02", "2024-03")):
            visits.append((pid, ym, base + 1000 * k, base // 20 + 50 * k, "189,190"))
    conn.executemany(
        "INSERT INTO sight_visits(place_id, year_month, domestic, foreign_, source_id) VALUES (?, ?, ?, ?, ?)",
        visits)
    conn.executemany(
        "INSERT INTO data_sources(source_id, name, url, period_actual, notes) VALUES (?, ?, ?, ?, ?)",
        [("1349", "모의 장소 목록", None, "mock", "모의 데이터"),
         ("563", "모의 읍면동 방문/거주", None, "2018-01~2022-09", "모의 데이터"),
         ("1208", "모의 렌터카 체류", None, "2021-07~12 토요일", "모의 데이터"),
         ("189,190", "모의 입장객 추이", None, "2024-01~2024-03", "모의 데이터")])
    meta_set(conn, "data_version", "mock")
    conn.commit()
    conn.close()
