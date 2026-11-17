"""M6 수정 (설계 6.5·6.6). 행동 선택은 LLM 또는 규칙, 적용·검증은 코드.

행동: replace(같은 권역 미사용 후보로 교체) / reorder(최근접 재정렬) / remove(제외).
"""
import copy

from malttara.geo import centroid, haversine_km
from malttara.tools.itinerary import order_nearest

ALLOWED_ACTIONS = ("replace", "reorder", "remove")


def _used(itinerary) -> set:
    return {pid for d in itinerary["days"] for pid in d["place_ids"]}


def _day(itinerary, day):
    return next((d for d in itinerary["days"] if d["day"] == day), None)


def apply_action(itinerary: dict, action: dict, candidates_by_region: dict, places: dict, pinned: set):
    """검증을 통과하면 새 일정(원본 불변), 아니면 None."""
    if not isinstance(action, dict) or action.get("type") not in ALLOWED_ACTIONS:
        return None
    d = _day(itinerary, action.get("day"))
    pid = action.get("place_id")
    if d is None or pid not in d["place_ids"]:
        return None
    t = action["type"]
    if t in ("replace", "remove") and pid in pinned:
        return None
    new = copy.deepcopy(itinerary)
    nd = _day(new, d["day"])
    if t == "replace":
        rep = action.get("replacement_id")
        allowed = {p["place_id"] for p in candidates_by_region.get(d["region_id"], [])}
        if rep not in allowed or rep in _used(itinerary) or rep not in places:
            return None
        idx = nd["place_ids"].index(pid)
        nd["place_ids"][idx] = rep
    elif t == "remove":
        nd["place_ids"].remove(pid)
    nd["place_ids"] = order_nearest(nd["place_ids"], places, None) if nd["place_ids"] else []
    return new


def _best_unused(itinerary, region, candidates_by_region):
    used = _used(itinerary)
    return next((p["place_id"] for p in candidates_by_region.get(region, []) if p["place_id"] not in used), None)


def rule_revision(itinerary: dict, violations: list, candidates_by_region: dict, places: dict, pinned: set):
    """규칙 폴백: 고칠 수 있는 첫 위반에 대한 행동. 없으면 None."""
    for v in violations:
        d = _day(itinerary, v["day"])
        if d is None:
            continue
        if v["type"] in ("distance", "regions"):
            movable = [i for i in d["place_ids"] if i not in pinned and i in places]
            if not movable:
                continue
            foreign = [i for i in movable if places[i]["region_id"] != d["region_id"]]
            if foreign:
                target = foreign[0]
            else:
                c = centroid([(places[i]["lat"], places[i]["lon"]) for i in d["place_ids"] if i in places])
                target = max(movable, key=lambda i: (haversine_km(c[0], c[1], places[i]["lat"], places[i]["lon"]), i))
            rep = _best_unused(itinerary, d["region_id"], candidates_by_region)
            if rep:
                return {"type": "replace", "day": d["day"], "place_id": target, "replacement_id": rep}
            if foreign:
                return {"type": "remove", "day": d["day"], "place_id": target}
        elif v["type"] in ("duplicate", "out_of_scope"):
            target = v["place_id"]
            if target in pinned:
                continue
            rep = _best_unused(itinerary, d["region_id"], candidates_by_region)
            if rep and target in places:
                return {"type": "replace", "day": d["day"], "place_id": target, "replacement_id": rep}
            return {"type": "remove", "day": d["day"], "place_id": target}
    return None


def inject_error(itinerary: dict, scored: list, places: dict, settings: dict):
    """오류 주입 시연: 1일차 마지막 장소를 다른 권역 장소로 바꾼다. 반환 (새 일정, 넣은 place_id)."""
    new = copy.deepcopy(itinerary)
    d1 = new["days"][0]
    used = _used(itinerary)
    ex = (settings.get("inject_example") or {}).get("place_id")
    pick = None
    if ex and ex in places and ex not in used and places[ex]["region_id"] != d1["region_id"]:
        pick = ex
    if pick is None:
        pick = next((p["place_id"] for p in scored
                     if p["region_id"] != d1["region_id"] and p["place_id"] not in used and not p.get("slot")), None)
    if pick is None or not d1["place_ids"]:
        return new, None
    d1["place_ids"][-1] = pick
    return new, pick
