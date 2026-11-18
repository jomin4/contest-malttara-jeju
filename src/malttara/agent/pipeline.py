"""Batch A·B가 함께 쓰는 단계: 검증·수정 루프, 결과 조립."""
import json

from malttara.agent.decide import decide, polish_text
from malttara.agent.prompts import REVISE_SYSTEM
from malttara.db import data_sources
from malttara.tools.explain import explain_place, summary_template
from malttara.tools.places import check_data_quality
from malttara.tools.quests import generate_quests
from malttara.tools.revise import apply_action, rule_revision
from malttara.tools.route import calculate_route
from malttara.tools.validate import validate_itinerary

PLACE_FIELDS = ("place_id", "name", "lat", "lon", "emd", "region_id", "region_name", "category", "category_source",
                "overview", "source", "score", "interest", "spread", "quiet", "indicators", "has_trend", "slot")

REVISE_SCHEMA = {
    "type": "object", "required": ["type", "day", "place_id"], "additionalProperties": False,
    "properties": {"type": {"enum": ["replace", "reorder", "remove"]}, "day": {"type": "integer"},
                   "place_id": {"type": "string"}, "replacement_id": {"type": ["string", "null"]}},
}


def violation_text(v: dict, places: dict) -> str:
    t, d = v["type"], v["day"]
    name = places.get(v.get("place_id") or "", {}).get("name", v.get("place_id"))
    return {
        "distance": f"{d}일차 직선 합계 {v['value']} km > 기준 {v['limit']} km",
        "regions": f"{d}일차 방문 권역 {v['value']}곳 > 기준 {v['limit']}곳",
        "duplicate": f"{d}일차 '{name}' 중복",
        "out_of_scope": f"{d}일차 '{name}' 범위 밖 장소",
        "count": f"{d}일차 장소 {v['value']}곳 (목표 {v['limit']}곳) — 조건에 맞는 후보 부족",
        "origin": f"1일차 출발지에서 첫 장소까지 직선 {v['value']} km > 기준 {v['limit']} km",
    }.get(t, t)


def _pinned_regions(v, itinerary, places, pinned) -> bool:
    """권역 위반이 사용자가 고정한(꼭 갈래요·직접 고름) 장소 때문이면 자동 수정 대상이 아니다(원칙 7)."""
    if v["type"] != "regions" or not pinned:
        return False
    d = next((x for x in itinerary["days"] if x["day"] == v["day"]), None)
    off = [i for i in (d or {}).get("place_ids", []) if (places.get(i) or {}).get("region_id") != d["region_id"]]
    return bool(off) and all(i in pinned for i in off)


def revise_loop(conn, state, itinerary, places, candidates_by_region, goal, settings, llm, pinned=frozenset(),
                origin_xy=None):
    """검증 → (위반 시) 행동 선택 → 적용, 최대 max_revisions회. 반환 (일정, 남은 위반)."""
    for attempt in range(settings["max_revisions"] + 1):
        violations = validate_itinerary(itinerary, places, goal, settings, origin_xy)
        if not violations:
            state.emit("validate_itinerary", "code", "ok", "검증 통과: 위반 없음")
            return itinerary, []
        for v in violations:
            state.emit("validate_itinerary", "code", "fail", violation_text(v, places))
        fixable = [v for v in violations if v["type"] != "count" and not _pinned_regions(v, itinerary, places, pinned)]
        if attempt == settings["max_revisions"] or not fixable:
            if not fixable:
                state.emit("revise_itinerary", "code", "skip", "자동으로 고칠 수 있는 위반 없음 → 화면에 표시")
            else:
                state.emit("revise_itinerary", "code", "skip", f"수정 {settings['max_revisions']}회 후에도 위반이 남아 사용자에게 넘김")
            return itinerary, violations
        day_info = {d["day"]: {"region_id": d["region_id"], "place_ids": d["place_ids"]} for d in itinerary["days"]}
        cands = {r: [p["place_id"] for p in lst[:8]] for r, lst in candidates_by_region.items()}
        user = json.dumps({"violations": violations, "days": day_info, "candidates_by_region": cands,
                           "pinned": sorted(pinned)}, ensure_ascii=False)
        action, actor = decide(conn, state.batch_id, "revise", llm, REVISE_SYSTEM, user, REVISE_SCHEMA,
                               accept=lambda a: apply_action(itinerary, a, candidates_by_region, places, pinned) is not None,
                               fallback=lambda: rule_revision(itinerary, violations, candidates_by_region, places, pinned),
                               options=violations)
        new = apply_action(itinerary, action, candidates_by_region, places, pinned) if action else None
        if new is None:
            state.emit("revise_itinerary", actor, "skip", "적용할 수 있는 수정 행동 없음 → 화면에 표시")
            return itinerary, violations
        old = places.get(action["place_id"], {}).get("name", action["place_id"])
        if action["type"] == "replace":
            msg = f"{action['day']}일차 '{old}' → '{places[action['replacement_id']]['name']}' 교체 (같은 권역)"
        elif action["type"] == "remove":
            msg = f"{action['day']}일차 '{old}' 제외"
        else:
            msg = f"{action['day']}일차 순서 재정렬"
        state.emit("revise_itinerary", actor, "fix", msg)
        itinerary = new
    return itinerary, validate_itinerary(itinerary, places, goal, settings, origin_xy)


def alternatives_for(itinerary, scored, settings) -> dict:
    used = {pid for d in itinerary["days"] for pid in d["place_ids"]}
    n = settings["alternatives_per_place"]
    by_key = {}
    for p in scored:
        by_key.setdefault((p["region_id"], p.get("slot")), []).append(p["place_id"])
    out = {}
    pmap = {p["place_id"]: p for p in scored}
    for d in itinerary["days"]:
        for pid in d["place_ids"]:
            p = pmap.get(pid)
            if not p:
                continue
            pool = by_key.get((d["region_id"], p.get("slot")), [])
            out[pid] = [x for x in pool if x not in used][:n]
    return out


def compact(p: dict) -> dict:
    return {k: p.get(k) for k in PLACE_FIELDS}


def assemble_result(conn, state, goal, itinerary, scored, violations, settings, interests_cfg, llm,
                    extra_place_ids=(), diff=None) -> dict:
    pmap = {p["place_id"]: p for p in scored}
    routes = calculate_route(itinerary, pmap)
    alts = alternatives_for(itinerary, scored, settings)
    ids = [pid for d in itinerary["days"] for pid in d["place_ids"]]
    all_ids = set(ids) | {a for v in alts.values() for a in v} | {i for i in extra_place_ids if i in pmap}
    places = {pid: compact(pmap[pid]) for pid in sorted(all_ids) if pid in pmap}
    result = {
        "batch_id": state.batch_id, "kind": state.kind, "prev_batch_id": state.prev_batch_id,
        "goal": goal, "itinerary": itinerary, "places": places, "routes": routes,
        "violations_remaining": violations,
        "explanations": {pid: explain_place(places[pid], goal, interests_cfg) for pid in ids if pid in places},
        "summary": None, "quests": generate_quests(itinerary, places), "alternatives": alts,
        "quality": check_data_quality([places[i] for i in ids if i in places]), "diff": diff,
    }
    text, actor = polish_text(llm, summary_template(result))
    result["summary"] = text
    state.emit("explain_decisions", actor, "ok", "설명 문장 생성" + (" (AI 다듬기)" if actor == "llm" else " (템플릿)"))
    state.goal = goal
    state.finish(result)
    state.save(conn)
    state.emit("save_agent_state", "code", "ok", f"배치 {state.batch_id} 저장")
    return result


def sources(conn) -> list:
    return data_sources(conn)
