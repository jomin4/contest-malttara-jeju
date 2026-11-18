"""Batch B — 미리보기 반응을 반영한 재설계 (설계 6.7).

사용자 선택이 우선한다(원칙 7): 꼭 갈래요는 항상 고정, 별로예요는 항상 교체. LLM은 나머지 유지·교체만 고른다.
"""
import copy
import json

from malttara.agent.decide import decide
from malttara.agent.pipeline import assemble_result, revise_loop
from malttara.agent.schema_lite import check_schema
from malttara.tools.compare import compare_itineraries
from malttara.tools.feedback import analyze_feedback, load_events
from malttara.tools.itinerary import order_nearest, pace_k
from malttara.tools.places import score_places

REDESIGN_SCHEMA = {
    "type": "object", "required": ["decisions"], "additionalProperties": False,
    "properties": {"decisions": {"type": "array", "items": {
        "type": "object", "required": ["place_id", "decision"], "additionalProperties": False,
        "properties": {"place_id": {"type": "string"}, "decision": {"enum": ["keep", "pin", "replace"]}}}}},
}
REDESIGN_SYSTEM = ("너는 사용자 반응(꼭 갈래요·관심·별로예요)을 보고 기존 일정의 각 장소를 keep/pin/replace 중 하나로 정한다. "
                   "꼭 갈래요는 pin, 별로예요는 replace로 정해야 한다. 주어진 place_id만 쓴다.")


def accept_redesign(out: dict, fb: dict, prev_ids: set) -> bool:
    if not check_schema(out, REDESIGN_SCHEMA):
        return False
    for d in out["decisions"]:
        if d["place_id"] not in prev_ids:
            return False
        if d["place_id"] in fb["pinned"] and d["decision"] != "pin":
            return False
        if d["place_id"] in fb["disliked"] and d["decision"] in ("keep", "pin"):
            return False
    return True


def rule_redesign(prev_ids: list, fb: dict) -> dict:
    return {"decisions": [{"place_id": p, "decision": "pin" if p in fb["pinned"] else
                           "replace" if p in fb["disliked"] else "keep"} for p in prev_ids]}


def place_picks(new_it, picks, pmap, pinned, used, scored_rank):
    """직접 고른 장소를 일정에 넣는다. 같은 날의 고정 안 된 장소 중 점수가 가장 낮은 곳과 바꿔 하루 장소 수(k)를 지킨다.
    날짜 지정이 없으면 같은 권역의 날 → 없으면 고정이 가장 적은 날. 반환 ({빠진 id: 들어간 id}, [추가만 된 id])."""
    swapped, appended = {}, []
    days = {d["day"]: d for d in new_it["days"]}
    for pk in picks:
        pid = pk["place_id"]
        if pid in used or pid not in pmap:
            continue
        d = days.get(pk.get("day")) or next((x for x in new_it["days"] if x["region_id"] == pmap[pid]["region_id"]), None) \
            or min(new_it["days"], key=lambda x: sum(i in pinned for i in x["place_ids"]))
        free = [i for i in d["place_ids"] if i not in pinned]
        same = [i for i in free if (pmap.get(i) or {}).get("slot") == pmap[pid].get("slot")]
        free = same or free
        if free:
            out = max(free, key=lambda i: scored_rank.get(i, 10 ** 9))
            d["place_ids"] = [pid if i == out else i for i in d["place_ids"]]
            swapped[out] = pid
            used.discard(out)
        else:
            d["place_ids"].append(pid)
            appended.append(pid)
        used.add(pid)
    return swapped, appended


def run_batch_b(conn, prev_batch_id, llm, settings, interests_cfg, regions_cfg, state, picks=None):
    row = conn.execute("SELECT goal_json, result_json FROM batches WHERE batch_id = ?", (prev_batch_id,)).fetchone()
    if row is None or not row["result_json"] or row["result_json"] == "null":
        msg = "이전 경로를 찾을 수 없습니다. 처음부터 다시 시작해 주세요"
        state.emit("load_state", "code", "fail", msg)
        state.fail(msg)
        return None
    prev = json.loads(row["result_json"])
    goal = prev["goal"]
    state.goal = goal
    state.emit("load_state", "code", "ok", f"이전 배치 {prev_batch_id} 불러옴")

    fb = analyze_feedback(load_events(conn, prev_batch_id), prev["places"])
    state.emit("analyze_feedback", "code", "ok",
               f"꼭 갈래요 {len(fb['pinned'])} · 별로예요 {len(fb['disliked'])} · 관심 분류 "
               + (", ".join(fb["liked_categories"]) or "없음") + f" · 가상 도착 {len(fb['arrived'])}곳")

    picks = [x for x in (picks or []) if x.get("place_id")]
    picked = {x["place_id"] for x in picks}
    if picks:                                           # 직접 고른 장소 = 꼭 갈래요와 같은 대우(원칙 7)
        fb["pinned"] |= picked
        fb["disliked"] -= picked
        state.emit("analyze_feedback", "code", "ok", f"직접 고른 장소 {len(picks)}곳 → 고정")

    boosts = {c: settings["feedback_interest_boost"] for c in fb["liked_categories"]}
    scored = score_places(conn, goal, settings, interests_cfg, boosts)
    pmap = {p["place_id"]: p for p in scored}
    if boosts:
        state.emit("search_places", "code", "ok", "선호 분류 가중을 반영해 후보 점수 재계산")

    prev_it = prev["itinerary"]
    prev_ids = [pid for d in prev_it["days"] for pid in d["place_ids"]]
    plan, actor = decide(conn, state.batch_id, "redesign", llm, REDESIGN_SYSTEM,
                         json.dumps({"places": prev_ids, "pinned": sorted(fb["pinned"]), "disliked": sorted(fb["disliked"]),
                                     "liked_categories": fb["liked_categories"]}, ensure_ascii=False),
                         REDESIGN_SCHEMA, lambda o: accept_redesign(o, fb, set(prev_ids)),
                         lambda: rule_redesign(prev_ids, fb))
    decision = {d["place_id"]: d["decision"] for d in plan["decisions"]}
    for p in prev_ids:                                  # 사용자 선택은 코드가 한 번 더 강제
        decision[p] = "pin" if p in fb["pinned"] else "replace" if p in fb["disliked"] else decision.get(p, "keep")
    state.emit("decide_keep_replace", actor, "ok",
               f"고정 {sum(v == 'pin' for v in decision.values())} · 교체 {sum(v == 'replace' for v in decision.values())} · "
               f"유지 {sum(v == 'keep' for v in decision.values())}")

    new_it = copy.deepcopy(prev_it)
    used = set(prev_ids)
    replaced, added = {}, {}
    k = pace_k(goal, settings)
    for d in new_it["days"]:
        ids = []
        for pid in d["place_ids"]:
            if decision.get(pid) != "replace":
                ids.append(pid)
                continue
            slot = (pmap.get(pid) or {}).get("slot")
            rep = next((p["place_id"] for p in scored if p["region_id"] == d["region_id"] and p.get("slot") == slot
                        and p["place_id"] not in used and p["place_id"] not in fb["disliked"]), None)
            if rep:
                ids.append(rep)
                used.add(rep)
                replaced[pid] = rep
                state.emit("search_places", "code", "fix",
                           f"{d['day']}일차 '{prev['places'][pid]['name']}' → '{pmap[rep]['name']}'")
        while len(ids) < k:
            extra = next((p for p in scored if p["region_id"] == d["region_id"] and not p.get("slot")
                          and p["place_id"] not in used and p["place_id"] not in fb["disliked"]), None)
            if extra is None:
                break
            ids.append(extra["place_id"])
            used.add(extra["place_id"])
            added[extra["place_id"]] = extra.get("category")
            state.emit("search_places", "code", "add", f"{d['day']}일차 '{extra['name']}' 추가")
        if ids != d["place_ids"]:
            d["place_ids"] = order_nearest(ids, pmap, None)

    if picks:
        rank = {p["place_id"]: i for i, p in enumerate(scored)}
        swapped, appended = place_picks(new_it, picks, pmap, fb["pinned"], used, rank)
        for out_id, in_id in swapped.items():
            day = next(d["day"] for d in new_it["days"] if in_id in d["place_ids"])
            name = (prev["places"].get(out_id) or pmap.get(out_id) or {}).get("name", out_id)
            state.emit("search_places", "code", "fix", f"{day}일차 '{name}' → '{pmap[in_id]['name']}' (직접 고름)")
            if out_id in replaced.values():             # 방금 대안으로 들어온 곳을 다시 뺀 경우
                replaced = {k: (in_id if v == out_id else v) for k, v in replaced.items()}
            elif out_id in added:
                added.pop(out_id)
                added[in_id] = pmap[in_id].get("category")
            else:
                replaced[out_id] = in_id
        for in_id in appended:
            added[in_id] = pmap[in_id].get("category")
            state.emit("search_places", "code", "add", f"'{pmap[in_id]['name']}' 추가 (직접 고름, 그날 장소가 모두 고정이라 늘어남)")
        for d in new_it["days"]:
            d["place_ids"] = order_nearest(d["place_ids"], pmap, None)

    cands = {}
    for p in scored:
        if p["place_id"] not in fb["disliked"]:
            cands.setdefault(p["region_id"], []).append(p)
    new_it, remaining = revise_loop(conn, state, new_it, pmap, cands, goal, settings, llm, pinned=frozenset(fb["pinned"]))
    diff = compare_itineraries(prev_it, new_it, fb, replaced, added, picked=picked)
    state.emit("compare_itineraries", "code", "ok",
               " · ".join(f"{c} {sum(x['change'] == c for x in diff)}" for c in ("keep", "pin", "replace", "add", "remove")))
    extra_ids = {x["place_id"] for x in diff} | {x["replaced_by"] for x in diff if x["replaced_by"]}
    return assemble_result(conn, state, goal, new_it, scored, remaining, settings, interests_cfg, llm,
                           extra_place_ids=extra_ids, diff=diff)
