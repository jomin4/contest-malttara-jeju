"""M5 일정 생성 (설계 6.3). 권역 하나에 하루, 최근접 이웃 순서, 음식·카페는 하루 1곳씩 가운데."""
import re

from malttara.geo import haversine_km


def pace_k(goal: dict, settings: dict) -> int:
    return settings["pace_k"][goal.get("pace") or settings["default_pace"]]


def order_nearest(place_ids: list, places: dict, start=None) -> list:
    if not place_ids:
        return []
    rest = list(place_ids)
    if start is None:
        cur = rest.pop(0)
    else:
        cur = min(rest, key=lambda i: (haversine_km(start[0], start[1], places[i]["lat"], places[i]["lon"]), i))
        rest.remove(cur)
    order = [cur]
    while rest:
        c = places[cur]
        cur = min(rest, key=lambda i: (haversine_km(c["lat"], c["lon"], places[i]["lat"], places[i]["lon"]), i))
        rest.remove(cur)
        order.append(cur)
    return order


def _norm(name: str) -> str:
    return re.sub(r"\(.*?\)|[\s·.,\-]", "", name or "").lower()


def resolve_origin(conn, origin):
    """출발지 문자열과 정규화 이름이 같은 장소의 좌표. 없으면 None(→ 미반영)."""
    if not origin:
        return None
    key = _norm(origin)
    for r in conn.execute("SELECT name, lat, lon FROM places WHERE in_scope = 1 ORDER BY place_id"):
        if _norm(r["name"]) == key:
            return (r["lat"], r["lon"])
    return None


def _merge_middle(general: list, slot_ids: list) -> list:
    total = len(general) + len(slot_ids)
    mid = max(0, total // 2 - len(slot_ids) // 2)
    mid = min(mid, len(general))
    return general[:mid] + slot_ids + general[mid:]


def create_itinerary(candidates: list, slot_candidates: dict, goal: dict, settings: dict,
                     origin_xy=None, region_order=None) -> dict:
    """candidates·slot_candidates는 점수 내림차순 Place 목록. 반환: 계약 Itinerary."""
    k = pace_k(goal, settings)
    days = goal["days"]
    order_idx = {r: i for i, r in enumerate(region_order or [])}
    places = {p["place_id"]: p for p in candidates}
    for lst in slot_candidates.values():
        places.update({p["place_id"]: p for p in lst})

    by_region = {}
    for p in candidates:
        by_region.setdefault(p["region_id"], []).append(p)
    # 후보가 k개 미만인 권역은 뒤로(인접 권역 확장 대신 배정 순서로 처리), 그다음 상위 k개 점수 합
    ranked = sorted(by_region, key=lambda r: (len(by_region[r]) < k,
                                               -sum(p["score"] for p in by_region[r][:k]),
                                               order_idx.get(r, 99), r))

    used = set()
    out = []
    for day in range(1, days + 1):
        if not ranked:
            out.append({"day": day, "region_id": None, "place_ids": []})
            continue
        region = ranked[(day - 1) % len(ranked)]
        slot_ids = []
        for key in slot_candidates:
            pick = next((p["place_id"] for p in slot_candidates[key]
                         if p["region_id"] == region and p["place_id"] not in used), None)
            if pick:
                slot_ids.append(pick)
                used.add(pick)
        general = [p["place_id"] for p in by_region[region] if p["place_id"] not in used][:max(0, k - len(slot_ids))]
        used.update(general)
        start = origin_xy if day == 1 else None
        ordered = order_nearest(general, places, start)
        out.append({"day": day, "region_id": region, "place_ids": _merge_middle(ordered, slot_ids)})
    return {"days": out}
