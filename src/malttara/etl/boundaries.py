"""행정동 경계(GeoJSON) → 점-다각형 판정용 다각형, 화면용 map.json(개발 PC 전용 ETL).

원자료: 통계청 SGIS 행정동 경계를 가공한 vuski/admdongkor ver20261001(CC BY 4.0, 원자료 공공누리 1유형)
  https://raw.githubusercontent.com/vuski/admdongkor/master/ver20261001/HangJeongDong_ver20261001.geojson
파일 좌표계는 urn:ogc:def:crs:OGC:1.3:CRS84(WGS84 경도·위도)라 변환 없이 표준 라이브러리로만 읽는다.
좌표계가 CRS84/EPSG:4326이 아니면 멈춘다(그때 pyproj 변환을 추가한다).

emd 키: adm_nm에서 "제주특별자치도 "를 뗀 "{시} {읍면동}"(예: "제주시 애월읍").
"""
import json
import math
import os

from malttara.etl.clean_places import assign_region

SIDO_PREFIX = "제주특별자치도 "
REF_LAT_DEG = 33.4          # 등장방형 투영의 기준 위도(계약: cos(33.4°))
MAP_WIDTH = 1000            # view_box 가로(프론트 권장 W ≈ 1000)
MAP_PADDING = 10            # view_box 가장자리 여백
ATTRIBUTION = "SGIS 행정동 경계(가공: vuski/admdongkor ver20261001, CC BY 4.0)"
_WGS84_NAMES = ("CRS84", "EPSG::4326", "EPSG:4326")


def _check_crs(data: dict) -> None:
    name = ((data.get("crs") or {}).get("properties") or {}).get("name", "")
    if name and not any(n in name for n in _WGS84_NAMES):
        raise ValueError(f"WGS84가 아닌 좌표계입니다: {name} (pyproj 변환이 필요)")


def _jeju_features(boundary_path: str) -> list:
    """제주특별자치도 행정동 feature만 [(emd, [[ [lon, lat], ... ] 고리, ...]), ...]로."""
    with open(boundary_path, encoding="utf-8") as f:
        data = json.load(f)
    _check_crs(data)
    out = []
    for feat in data.get("features", []):
        nm = (feat.get("properties") or {}).get("adm_nm", "")
        if not nm.startswith(SIDO_PREFIX):
            continue
        geom = feat.get("geometry") or {}
        if geom.get("type") == "Polygon":
            polys = [geom["coordinates"]]
        elif geom.get("type") == "MultiPolygon":
            polys = geom["coordinates"]
        else:
            continue
        rings = [ring for poly in polys for ring in poly]
        out.append((nm[len(SIDO_PREFIX):].strip(), rings))
    return out


def load_polygons(boundary_path: str, alias: "dict | None" = None) -> list:
    """emd_of_point용 다각형 [(emd, [고리, ...]), ...]. 고리 점은 (lat, lon). 바깥·구멍 고리 모두 넣는다."""
    alias = alias or {}
    out = []
    for emd, rings in _jeju_features(boundary_path):
        out.append((alias.get(emd, emd), [[(float(p[1]), float(p[0])) for p in ring] for ring in rings]))
    return out


def nearest_emd(lat: float, lon: float, polygons: list, max_km: float) -> "str | None":
    """경계선까지 가장 가까운 읍면동(max_km 이내). 해안선 바로 바깥 좌표(해변·포구 등)용.

    기준 위도의 등장방형 근사(km)로 점-선분 거리를 잰다. max_km 밖이면 None.
    """
    kx = 111.32 * math.cos(math.radians(lat))
    ky = 110.57
    p = (lon * kx, lat * ky)
    best_d, best_emd = max_km, None
    dlat = max_km / ky
    for emd, rings in polygons:
        for ring in rings:
            for (la1, lo1), (la2, lo2) in zip(ring, ring[1:]):
                if min(la1, la2) - dlat > lat or max(la1, la2) + dlat < lat:
                    continue
                d = _seg_dist(p, (lo1 * kx, la1 * ky), (lo2 * kx, la2 * ky))
                if d <= best_d:
                    best_d, best_emd = d, emd
    return best_emd


def find_boundary_file(raw_dir: str) -> "str | None":
    """raw_dir/boundary/ 아래 첫 .geojson 경로(이름순). 없으면 None."""
    d = os.path.join(raw_dir, "boundary")
    if not os.path.isdir(d):
        return None
    files = sorted(f for f in os.listdir(d) if f.lower().endswith((".geojson", ".json")))
    return os.path.join(d, files[0]) if files else None


def _seg_dist(p: tuple, a: tuple, b: tuple) -> float:
    (px, py), (ax, ay), (bx, by) = p, a, b
    dx, dy = bx - ax, by - ay
    if dx == 0 and dy == 0:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def _dp(points: list, tolerance: float) -> list:
    """열린 선의 Douglas–Peucker(반복문, 양 끝점 유지)."""
    n = len(points)
    if n < 3:
        return list(points)
    keep = [False] * n
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i, j = stack.pop()
        best, idx = -1.0, -1
        for k in range(i + 1, j):
            d = _seg_dist(points[k], points[i], points[j])
            if d > best:
                best, idx = d, k
        if idx != -1 and best > tolerance:
            keep[idx] = True
            stack.append((i, idx))
            stack.append((idx, j))
    return [p for p, k in zip(points, keep) if k]


def simplify_ring(ring: list, tolerance: float) -> list:
    """닫힌 고리 단순화. 첫 점과 가장 먼 점에서 둘로 나눠 각각 DP → 닫힌 고리로 돌려준다.

    서로 다른 점이 3개 미만으로 줄면 빈 목록(작은 바위섬 조각 등은 화면에서 뺀다).
    """
    pts = list(ring)
    if len(pts) > 1 and pts[0] == pts[-1]:
        pts = pts[:-1]
    if len(pts) < 3:
        return []
    far = max(range(len(pts)), key=lambda k: math.hypot(pts[k][0] - pts[0][0], pts[k][1] - pts[0][1]))
    left = _dp(pts[: far + 1], tolerance)
    right = _dp(pts[far:] + [pts[0]], tolerance)
    out = left[:-1] + right
    if len(set(out)) < 3:
        return []
    return out


def _fmt(v: float) -> str:
    s = f"{v:.1f}"
    return s[:-2] if s.endswith(".0") else s


def _path(rings: list) -> str:
    """투영된 고리들 → SVG path d. 소수 1자리, 연속 중복 점 제거."""
    parts = []
    for ring in rings:
        pts = []
        for x, y in ring:
            q = (_fmt(x), _fmt(y))
            if not pts or pts[-1] != q:
                pts.append(q)
        if len(pts) > 1 and pts[0] == pts[-1]:
            pts = pts[:-1]
        if len(set(pts)) < 3:
            continue
        parts.append("M" + pts[0][0] + "," + pts[0][1] + "L" + " ".join(f"{x},{y}" for x, y in pts[1:]) + "Z")
    return "".join(parts)


def build_map(boundary_path: str, regions_cfg: dict, alias: dict, out_path: str, tolerance: float) -> dict:
    """행정동 경계 → 계약 `GET /api/map` 모양 JSON(파일로도 저장).

    - 권역이 없는 읍면동(부속섬: 우도면·추자면)은 뺀다.
    - 투영: x = (lon - min_lon) * scale * cos(33.4°), y = (max_lat - lat) * scale.
      min_lon·max_lat은 여백(MAP_PADDING)만큼 넓힌 값이라 모든 점이 0 이상이다. 가로는 MAP_WIDTH.
    - tolerance: 투영 좌표(view_box 단위) 기준 Douglas–Peucker 허용 오차.
    - 권역 외곽선은 같은 권역 읍면동 path를 이어 붙인 것(겹친 선 허용). 권역은 regions.json 순서 4개 모두.
    """
    feats = []
    for emd, rings in _jeju_features(boundary_path):
        emd = alias.get(emd, emd)
        rid = assign_region(emd, regions_cfg)
        if rid is None:
            continue
        feats.append((emd, rid, rings))
    if not feats:
        raise ValueError(f"권역에 속한 제주 읍면동 경계가 없습니다: {boundary_path}")

    lons = [p[0] for _, _, rings in feats for ring in rings for p in ring]
    lats = [p[1] for _, _, rings in feats for ring in rings for p in ring]
    cos_ref = math.cos(math.radians(REF_LAT_DEG))
    # 프론트가 같은 식을 쓰므로 반올림한 값으로 투영한다(내보내는 값 = 계산에 쓴 값)
    scale = round((MAP_WIDTH - 2 * MAP_PADDING) / ((max(lons) - min(lons)) * cos_ref), 4)
    min_lon = round(min(lons) - MAP_PADDING / (scale * cos_ref), 7)
    max_lat = round(max(lats) + MAP_PADDING / scale, 7)
    height = math.ceil((max_lat - min(lats)) * scale + MAP_PADDING)

    def proj(lon: float, lat: float) -> tuple:
        return ((lon - min_lon) * scale * cos_ref, (max_lat - lat) * scale)

    emds = []
    for emd, rid, rings in sorted(feats, key=lambda t: t[0]):
        simplified = []
        for ring in rings:
            r = simplify_ring([proj(p[0], p[1]) for p in ring], tolerance)
            if r:
                simplified.append(r)
        d = _path(simplified)
        if d:
            emds.append({"emd": emd, "region_id": rid, "d": d})

    regions = []
    for r in regions_cfg["regions"]:
        regions.append({
            "region_id": r["region_id"],
            "name": r["name"],
            "d": "".join(e["d"] for e in emds if e["region_id"] == r["region_id"]),
        })
    out = {
        "view_box": f"0 0 {MAP_WIDTH} {height}",
        "emds": emds,
        "regions": regions,
        "project": {"min_lon": min_lon, "max_lat": max_lat, "scale": scale},
        "attribution": ATTRIBUTION,
    }
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, separators=(",", ":"))
    return out
