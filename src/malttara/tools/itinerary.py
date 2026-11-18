"""M5 일정 생성 (설계 6.3). 권역 하나에 하루, 최근접 이웃 순서, 음식·카페는 하루 1곳씩 이동거리가 가장 적게 느는 자리에."""
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


DUP_KM = 0.5   # 일반 장소끼리 이 거리 안이면 같은 곳의 다른 기록으로 본다(예: 삼양해수욕장 / 삼양 검은모래해변)


def _core(name: str) -> str:
    return re.sub(r"제주|자연", "", _norm(name))


def _one_edit(a: str, b: str) -> bool:
    """글자 하나 다름(바꿈·빠짐) 이내 — 오타 기록(예: 절물/정물휴양림) 판별용."""
    if abs(len(a) - len(b)) > 1:
        return False
    if len(a) == len(b):
        return sum(x != y for x, y in zip(a, b)) <= 1
    if len(a) > len(b):
        a, b = b, a
    return any(a == b[:i] + b[i + 1:] for i in range(len(b)))


def is_duplicate(p: dict, chosen: list) -> bool:
    """이미 고른 장소와 같은 곳의 다른 기록인지. 이름이 같거나 한쪽이 다른 쪽을 포함(4자 이상),
    3km 안에서 이름이 한 글자만 다름(오타), 또는 둘 다 일반 장소(slot 없음)이고 DUP_KM 안."""
    n = _core(p.get("name", ""))
    for q in chosen:
        if q["place_id"] == p["place_id"]:
            return True
        m = _core(q.get("name", ""))
        if n and m and (n == m or (min(len(n), len(m)) >= 4 and (n in m or m in n))):
            return True
        a, b = _norm(p.get("name", "")), _norm(q.get("name", ""))
        if min(len(a), len(b)) >= 4 and (a in b or b in a):
            return True
        km = haversine_km(p["lat"], p["lon"], q["lat"], q["lon"])
        if min(len(n), len(m)) >= 4 and km < 3 and _one_edit(n, m):
            return True
        if not p.get("slot") and not q.get("slot") and km < DUP_KM:
            return True
    return False


def resolve_origin(conn, origin):
    """출발지 문자열과 정규화 이름이 같은 장소의 좌표. 없으면 None(→ 미반영)."""
    if not origin:
        return None
    key = _norm(origin)
    for r in conn.execute("SELECT name, lat, lon FROM places WHERE in_scope = 1 ORDER BY place_id"):
        if _norm(r["name"]) == key:
            return (r["lat"], r["lon"])
    return None


def _insert_best(order: list, pid: str, places: dict) -> list:
    """slot 장소를 직선 이동거리가 가장 적게 늘어나는 자리에 끼운다(맨 앞·맨 뒤 포함, 동률이면 앞자리)."""
    if not order:
        return [pid]
    best_i, best_add = 0, None
    p = places[pid]
    for i in range(len(order) + 1):
        prev = places[order[i - 1]] if i > 0 else None
        nxt = places[order[i]] if i < len(order) else None
        add = 0.0
        if prev:
            add += haversine_km(prev["lat"], prev["lon"], p["lat"], p["lon"])
        if nxt:
            add += haversine_km(p["lat"], p["lon"], nxt["lat"], nxt["lon"])
        if prev and nxt:
            add -= haversine_km(prev["lat"], prev["lon"], nxt["lat"], nxt["lon"])
        if best_add is None or add < best_add - 1e-9:
            best_i, best_add = i, add
    return order[:best_i] + [pid] + order[best_i:]


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
        if p.get("region_id") is None:           # 권역 없는 기록(예: '제주도')으로 하루를 만들지 않는다
            continue
        by_region.setdefault(p["region_id"], []).append(p)
    # 후보가 k개 미만인 권역은 뒤로(인접 권역 확장 대신 배정 순서로 처리), 그다음 상위 k개 점수 합
    ranked = sorted(by_region, key=lambda r: (len(by_region[r]) < k,
                                               -sum(p["score"] for p in by_region[r][:k]),
                                               order_idx.get(r, 99), r))

    chosen = []

    def take(p) -> bool:                         # 같은 곳의 다른 기록(이름 변형·0.5km 이내)이 두 번 들어가지 않게
        if is_duplicate(p, chosen):
            return False
        chosen.append(p)
        return True

    out = []
    for day in range(1, days + 1):
        if not ranked:
            out.append({"day": day, "region_id": None, "place_ids": []})
            continue
        region = ranked[(day - 1) % len(ranked)]
        slot_ids = []
        for key in slot_candidates:
            pick = next((p for p in slot_candidates[key] if p["region_id"] == region and take(p)), None)
            if pick:
                slot_ids.append(pick["place_id"])
        general = []
        for p in by_region[region]:
            if len(general) >= max(0, k - len(slot_ids)):
                break
            if take(p):
                general.append(p["place_id"])
        start = origin_xy if day == 1 else None
        ordered = order_nearest(general, places, start)
        for sid in slot_ids:
            ordered = _insert_best(ordered, sid, places)
        out.append({"day": day, "region_id": region, "place_ids": ordered})
    return {"days": out}
