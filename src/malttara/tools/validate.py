"""M6 일정 검증 (설계 6.4). 위반 목록은 코드가 만든다."""
from malttara.geo import haversine_km
from malttara.tools.itinerary import pace_k
from malttara.tools.route import calculate_route


def regions_limit(goal: dict, settings: dict) -> int:
    lim = settings["max_regions_per_day"]
    return lim.get(goal.get("pace") or "", lim["default"])


def validate_itinerary(itinerary: dict, places: dict, goal: dict, settings: dict, origin_xy=None) -> list:
    out = []
    k = pace_k(goal, settings)
    rlim = regions_limit(goal, settings)
    seen = set()
    valid = {pid: p for pid, p in places.items() if p.get("in_scope", 1)}
    routes = {}
    for d in itinerary["days"]:
        ids = [i for i in d["place_ids"] if i in valid]
        routes[d["day"]] = calculate_route({"days": [{"day": d["day"], "place_ids": ids}]}, valid)[0]
    for d in itinerary["days"]:
        day, ids = d["day"], d["place_ids"]
        total = routes[day]["total_km"]
        if total > settings["max_daily_km"]:
            out.append({"day": day, "type": "distance", "value": total, "limit": settings["max_daily_km"], "place_id": None})
        regs = {valid[i]["region_id"] for i in ids if i in valid}
        if len(regs) > rlim:
            out.append({"day": day, "type": "regions", "value": len(regs), "limit": rlim, "place_id": None})
        for pid in ids:
            if pid not in valid:
                out.append({"day": day, "type": "out_of_scope", "value": None, "limit": None, "place_id": pid})
            elif pid in seen:
                out.append({"day": day, "type": "duplicate", "value": None, "limit": None, "place_id": pid})
            seen.add(pid)
        if len(ids) != k:
            out.append({"day": day, "type": "count", "value": len(ids), "limit": k, "place_id": None})
        if origin_xy and day == 1 and ids and ids[0] in valid:
            first = valid[ids[0]]
            dist = round(haversine_km(origin_xy[0], origin_xy[1], first["lat"], first["lon"]), 1)
            if dist > settings["max_origin_km"]:
                out.append({"day": day, "type": "origin", "value": dist, "limit": settings["max_origin_km"], "place_id": ids[0]})
    return out
