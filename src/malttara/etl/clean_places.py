"""1349(VISIT JEJU 여행장소) 정제, 읍면동·권역 판정(표준 라이브러리만).

읍면동은 좌표로 정한다. 1349 지번주소에는 틀린 값이 있다
(예: 서로 다른 장소가 모두 "제주시 오라동 34-14"). 주소 파싱은 경계가 없을 때의 폴백이다.
"""
import re

from malttara.geo import haversine_km
from malttara.etl.names import normalize_name

_EMD_RE = re.compile(r"(제주시|서귀포시)\s+(\S+?(?:읍|면|동))(?=\s|$)")
DEFAULT_DEDUP_MAX_M = 50


def _in_ring(lat: float, lon: float, ring: list) -> bool:
    """ray-casting: (lat, lon)이 고리 안이면 True. 고리 점은 (lat, lon)."""
    inside = False
    n = len(ring)
    j = n - 1
    for i in range(n):
        yi, xi = ring[i]
        yj, xj = ring[j]
        if (yi > lat) != (yj > lat):
            x_cross = (xj - xi) * (lat - yi) / (yj - yi) + xi
            if lon < x_cross:
                inside = not inside
        j = i
    return inside


def emd_of_point(lat: float, lon: float, polygons: list) -> "str | None":
    """행정동 경계 [(emd, [고리, ...]), ...]에서 점이 든 읍면동. 경계 밖이면 None.

    한 읍면동의 고리들은 짝홀 규칙으로 합친다(여러 조각·구멍 모두 처리).
    """
    for emd, rings in polygons:
        inside = False
        for ring in rings:
            if _in_ring(lat, lon, ring):
                inside = not inside
        if inside:
            return emd
    return None


def parse_emd(jibun_address: str, alias: dict) -> "str | None":
    """지번주소에서 "{시} {읍면동}"을 뽑는다(경계가 없을 때만 쓰는 폴백). alias 우선."""
    m = _EMD_RE.search(jibun_address or "")
    if not m:
        return None
    key = f"{m.group(1)} {m.group(2)}"
    if key in alias:
        return alias[key]
    if m.group(2) in alias:
        return alias[m.group(2)]
    return key


def assign_region(emd: "str | None", regions_cfg: dict) -> "str | None":
    """읍면동 → 권역 id. `emds` 목록을 먼저 보고, 그다음 `dong_of`(해당 시의 '…동')."""
    if not emd:
        return None
    regions = regions_cfg.get("regions", [])
    for r in regions:
        if emd in r.get("emds", []):
            return r["region_id"]
    for r in regions:
        city = r.get("dong_of")
        if city and emd.startswith(city + " ") and emd.endswith("동"):
            return r["region_id"]
    return None


def is_island(address: str, lat: float, lon: float, cfg: dict) -> bool:
    """부속섬이면 True: 주소 토큰(우도면 등) 또는 섬 원(비양도 등) 안."""
    addr = address or ""
    if any(tok in addr for tok in cfg.get("island_address_tokens", [])):
        return True
    name = cfg.get("_current_name") or ""
    if any(name.replace(" ", "").startswith(p) for p in cfg.get("island_name_prefixes", [])):
        return True
    for c in cfg.get("island_circles", []):
        if haversine_km(lat, lon, c["lat"], c["lon"]) <= c["r_km"]:
            return True
    return False


def is_non_place(name: str, cfg: dict) -> bool:
    """렌터카·공항·주차장처럼 여행 장소가 아닌 이름이면 True."""
    n = name or ""
    if any(k in n for k in cfg.get("non_place_keywords", [])):
        return True
    if n.strip().lower() in [j.lower() for j in cfg.get("junk_names", [])]:
        return True
    return len(re.findall(r"[가-힣]", n)) < cfg.get("min_hangul", 0)   # "dd", "123", "TERER" 같은 이름


def _in_bbox(lat: float, lon: float, bbox: dict) -> bool:
    return bbox["min_lat"] <= lat <= bbox["max_lat"] and bbox["min_lon"] <= lon <= bbox["max_lon"]


def _to_float(v) -> "float | None":
    try:
        return float(str(v).strip())
    except (TypeError, ValueError):
        return None


def clean_1349(rows: list, cfg: dict, regions_cfg: dict, alias: dict, polygons=None) -> list:
    """1349 행을 정제해 장소 dict 목록으로.

    bbox 밖·부속섬·비장소를 빼고, 같은 정규화 이름이 dedup 거리(기본 50m) 안에 있으면 앞의 것만 남긴다.
    emd: polygons가 있으면 좌표로 판정, 경계 밖(해안 등)이거나 polygons가 없으면 지번주소 폴백.
    place_id의 번호는 원본 데이터 행 번호(헤더 제외, 1부터).
    """
    prefixes = cfg.get("name_prefixes", [])
    dedup_km = cfg.get("dedup_max_m", DEFAULT_DEDUP_MAX_M) / 1000.0
    out = []
    seen = {}  # 정규화 이름 → [(lat, lon), ...]
    for idx, row in enumerate(rows, start=1):
        name = (row.get("장소명") or "").strip()
        lat, lon = _to_float(row.get("위도")), _to_float(row.get("경도"))
        if not name or lat is None or lon is None:
            continue
        jibun = (row.get("지번주소") or "").strip()
        address = jibun + " " + (row.get("도로명주소") or "").strip()
        if not _in_bbox(lat, lon, cfg["bbox"]):
            continue
        if is_island(address, lat, lon, dict(cfg, _current_name=name)) or is_non_place(name, cfg):
            continue
        key = normalize_name(name, prefixes)
        if any(haversine_km(lat, lon, a, b) <= dedup_km for a, b in seen.get(key, [])):
            continue
        seen.setdefault(key, []).append((lat, lon))

        emd = None
        if polygons:
            emd = emd_of_point(lat, lon, polygons)
            if emd is not None:
                emd = alias.get(emd, emd)
        if emd is None:
            emd = parse_emd(jibun, alias)
        out.append({
            "place_id": f"p1349-{idx:05d}",
            "name": name,
            "lat": lat,
            "lon": lon,
            "emd": emd,
            "region_id": assign_region(emd, regions_cfg),
            "source": "1349",
            "in_scope": 1,
        })
    return out
