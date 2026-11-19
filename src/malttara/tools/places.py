"""M3·M4 장소 점수·탐색·지역 지표·품질·관광 추이 (설계 6.2).

원칙 3: 읍면동 지표(563)와 장소 반경 지표(1208)는 다른 키(indicators.region / indicators.nearby)로 낸다.
"""
from malttara.config import load_config
from malttara.db import all_places, data_sources, emd_stats, place_trend, region_names
from malttara.geo import pct_rank
from malttara.regions import region_of_emd


def _slot_categories(interests_cfg: dict) -> dict:
    return {k: set(v["categories"]) for k, v in interests_cfg["interests"].items() if v.get("slot")}


def _period(conn, source_id: str):
    for s in data_sources(conn):
        if s["source_id"] == source_id:
            return s.get("period_actual")
    return None


def score_places(conn, goal: dict, settings: dict, interests_cfg: dict, boosts=None) -> list:
    boosts = boosts or {}
    interests = goal.get("interests") or []
    slots = _slot_categories(interests_cfg)
    wanted = set()
    for key in interests:
        spec = interests_cfg["interests"].get(key)
        if spec:
            wanted |= set(spec["categories"])
    general_wanted = any(not interests_cfg["interests"].get(k, {}).get("slot") for k in interests
                         if k in interests_cfg["interests"])
    w = settings["weights"]["quiet" if goal.get("quiet_pref") else "default"]
    neutral = settings["missing_indicator_value"]
    radius = settings["quiet_radius_km"]

    month = goal.get("month")
    stats = emd_stats(conn, month)
    ratios = [s["visit_ratio"] for s in stats.values() if s["visit_ratio"] is not None]
    places = all_places(conn)
    quiets = [p["quiet_count"] for p in places if p["quiet_count"]]          # 0건은 '한적'이 아니라 데이터 공백
    pops = [p.get("popularity") or 0 for p in places]
    names = region_names(conn)
    trend_ids = {r["place_id"] for r in conn.execute("SELECT DISTINCT place_id FROM sight_visits")}
    nearby_period = _period(conn, "1208")

    out = []
    for p in places:
        if general_wanted:
            interest = 1.0 if p["category"] in wanted else 0.0
        else:                                    # 관심사 미반영·음식/카페만 → 분류 있는 장소를 우선(분류 없음 0.5)
            interest = 1.0 if p["category"] else 0.5
        if interest and boosts.get(p["category"]):
            interest = min(1.2, interest + boosts[p["category"]])

        st = stats.get(p["emd"])
        if st and st["visit_ratio"] is not None:
            rpct = pct_rank(st["visit_ratio"], ratios)
            spread = 1 - rpct
            region_ind = {"emd": p["emd"], "visit_ratio": st["visit_ratio"], "pct": round(rpct, 4),
                          "period": st["period"], "month": month, "source_id": "563", "missing": False}
        else:
            spread = neutral
            region_ind = {"emd": p["emd"], "visit_ratio": None, "pct": None, "period": None,
                          "month": month, "source_id": "563", "missing": True}

        if p["quiet_count"]:
            qpct = pct_rank(p["quiet_count"], quiets)
            quiet = 1 - qpct
            nearby_ind = {"quiet_count": p["quiet_count"], "pct": round(qpct, 4), "radius_km": radius,
                          "period": nearby_period, "source_id": "1208", "missing": False}
        else:
            quiet = neutral
            nearby_ind = {"quiet_count": None, "pct": None, "radius_km": radius,
                          "period": nearby_period, "source_id": "1208", "missing": True}

        pop = pct_rank(p.get("popularity") or 0, pops) if any(pops) else 0.0
        q = dict(p)
        q.update({
            "region_name": names.get(p["region_id"]),
            "interest": round(interest, 4), "spread": round(spread, 4), "quiet": round(quiet, 4),
            "records": p.get("popularity") or 0,
            "popularity": round(pop, 4),
            "score": round(w[0] * interest + w[1] * spread + w[2] * quiet + (w[3] * pop if len(w) > 3 else 0), 6),
            "indicators": {"region": region_ind, "nearby": nearby_ind},
            "has_trend": p["place_id"] in trend_ids,
            "slot": next((k for k, cats in slots.items() if p["category"] in cats), None),
        })
        out.append(q)
    out.sort(key=lambda x: (-x["score"], x["place_id"]))
    return out


def search_places(conn, goal, settings, interests_cfg, region_ids=None, exclude_ids=None,
                  limit=50, boosts=None, slot=None, scored=None) -> list:
    """slot=None이면 slot 분류(음식·카페)를 뺀 일반 후보, slot='음식'이면 그 분류만."""
    exclude_ids = exclude_ids or set()
    rows = scored if scored is not None else score_places(conn, goal, settings, interests_cfg, boosts)
    out = []
    for p in rows:
        if p["place_id"] in exclude_ids:
            continue
        if region_ids and p["region_id"] not in region_ids:
            continue
        if slot is None and p["slot"] is not None:
            continue
        if slot is not None and p["slot"] != slot:
            continue
        out.append(p)
        if len(out) >= limit:
            break
    return out


def _region_items(conn, month, regions_cfg):
    stats = emd_stats(conn, month)
    ratios = [s["visit_ratio"] for s in stats.values() if s["visit_ratio"] is not None]
    items = []
    for emd, s in stats.items():
        v = s["visit_ratio"]
        items.append({"emd": emd, "region_id": region_of_emd(emd, regions_cfg), "visit_ratio": v,
                      "pct": None if v is None else round(pct_rank(v, ratios), 4)})
    period = next((s["period"] for s in stats.values() if s["period"]), _period(conn, "563"))
    return items, period


def get_region_data(conn, month, settings, regions_cfg=None) -> dict:
    regions_cfg = regions_cfg or load_config("regions")
    items, period = _region_items(conn, month, regions_cfg)
    return {"period": period, "source_id": "563", "month": month, "items": items}


def get_region_data_all(conn, settings, regions_cfg=None) -> dict:
    regions_cfg = regions_cfg or load_config("regions")
    months, period = {}, None
    for m in range(1, 13):
        items, p = _region_items(conn, m, regions_cfg)
        months[str(m)] = items
        period = period or (p if items else None)
    return {"period": period or _period(conn, "563"), "source_id": "563", "months": months}


def check_data_quality(places: list) -> dict:
    return {
        "no_category": sum(1 for p in places if not p.get("category")),
        "no_region_indicator": sum(1 for p in places if p["indicators"]["region"]["missing"]),
        "no_nearby_indicator": sum(1 for p in places if p["indicators"]["nearby"]["missing"]),
    }


def analyze_tourism(conn, place_ids: list) -> dict:
    out = {}
    for pid in place_ids:
        series = place_trend(conn, pid)
        if not series:
            continue
        yms = [s["year_month"] for s in series]
        out[pid] = {"place_id": pid, "period": f"{yms[0]}~{yms[-1]}", "source_ids": ["189", "190"],
                    "series": [{"year_month": s["year_month"], "domestic": s["domestic"],
                                "foreign": s["foreign"]} for s in series]}
    return out
