"""M5 거리 계산. 하버사인 직선거리만 쓴다(원칙 6: 이동 시간 아님)."""
from malttara.geo import haversine_km


def leg_km(a: dict, b: dict) -> float:
    return haversine_km(a["lat"], a["lon"], b["lat"], b["lon"])


def calculate_route(itinerary: dict, places: dict) -> list:
    out = []
    for d in itinerary["days"]:
        ids = d["place_ids"]
        legs = [round(leg_km(places[ids[i]], places[ids[i + 1]]), 1) for i in range(len(ids) - 1)]
        out.append({"day": d["day"], "legs_km": legs, "total_km": round(sum(legs), 1)})
    return out
