"""Batch A — 최초 경로 생성 (설계 3.3, 6장). 단계 골격은 코드가 고정한다."""
import json

from malttara.agent.decide import decide
from malttara.agent.pipeline import assemble_result, revise_loop
from malttara.agent.planner import PLAN_SCHEMA, accept_plan, enforce_required, plan_tasks_rules
from malttara.agent.prompts import PLAN_SYSTEM
from malttara.regions import region_order
from malttara.tools.goal import validate_goal
from malttara.tools.itinerary import create_itinerary, pace_k, resolve_origin
from malttara.tools.places import analyze_tourism, check_data_quality, get_region_data, score_places, search_places
from malttara.tools.revise import inject_error
from malttara.tools.route import calculate_route

GOAL_ERRORS = {"days": "여행 기간이 없습니다. 예: 2박 3일", "days_range": "여행 기간은 1~7일 사이로 입력해 주세요"}


def _goal_line(goal: dict) -> str:
    parts = [f"{goal['days']}일"]
    parts.append(f"여유 {goal['pace']}" if goal.get("pace") else "여유 미반영(보통 기준)")
    parts.append("관심 " + ", ".join(goal["interests"]) if goal.get("interests") else "관심 미반영")
    if goal.get("quiet_pref"):
        parts.append("한적함 요청")
    return " · ".join(parts)


def run_batch_a(conn, goal, inject, llm, settings, interests_cfg, regions_cfg, state):
    state.goal = goal
    errs = validate_goal(goal)
    if errs:
        msg = GOAL_ERRORS.get(errs[0], "조건을 확인해 주세요")
        state.emit("validate_goal", "code", "fail", msg)
        state.fail(msg)
        return None
    state.emit("validate_goal", "code", "ok", "조건 확인: " + _goal_line(goal))

    scored = score_places(conn, goal, settings, interests_cfg)
    pmap = {p["place_id"]: p for p in scored}
    general = search_places(conn, goal, settings, interests_cfg, limit=10_000, scored=scored)
    has_trend = any(p["has_trend"] for p in general[:200])

    rule_items = plan_tasks_rules(goal, has_trend, interests_cfg)
    plan, actor = decide(conn, state.batch_id, "plan_tasks", llm, PLAN_SYSTEM,
                         json.dumps({"goal": goal, "has_trend_candidates": has_trend}, ensure_ascii=False),
                         PLAN_SCHEMA, accept_plan, lambda: {"items": rule_items})
    items = enforce_required(plan["items"], goal, interests_cfg, has_trend) if actor == "llm" else plan["items"]
    for it in items:
        state.emit(it["tool"], actor, it["action"], it["reason"])
    added = {(it["tool"], (it.get("params") or {}).get("slot")) for it in items if it["action"] == "add"}

    state.emit("search_places", "code", "ok", f"일반 후보 {len(general)}곳 점수 계산 (상위 점수 {general[0]['score'] if general else 0})")
    slots = {}
    for key in goal.get("interests") or []:
        if ("search_slot", key) in added:
            slots[key] = search_places(conn, goal, settings, interests_cfg, slot=key, limit=10_000, scored=scored)
            state.emit("search_slot", "code", "ok", f"{key} 후보 {len(slots[key])}곳")
    if any(t == "get_region_data" for t, _ in added):
        rd = get_region_data(conn, goal.get("month"), settings, regions_cfg)
        vals = [i for i in rd["items"] if i["visit_ratio"] is not None]
        state.emit("get_region_data", "code", "ok", f"읍면동 {len(vals)}곳 방문/거주 비율 비교 (563 · {rd['period']})")
    if any(t == "analyze_tourism" for t, _ in added):
        tr = analyze_tourism(conn, [p["place_id"] for p in general[:200]])
        state.emit("analyze_tourism", "code", "ok", f"입장객 추이가 있는 후보 {len(tr)}곳 (189·190)")
    q = check_data_quality(general)
    state.emit("check_data_quality", "code", "ok",
               f"분류 없음 {q['no_category']} · 읍면동 지표 없음 {q['no_region_indicator']} · 반경 지표 없음 {q['no_nearby_indicator']}")

    k = pace_k(goal, settings)
    by_region = {}
    for p in general:
        by_region.setdefault(p["region_id"], []).append(p)
    short = [r for r in region_order(regions_cfg) if len(by_region.get(r, [])) < k]
    if short:
        state.emit("expand_regions", "code", "add", f"후보가 {k}곳 미만인 권역({', '.join(short)})은 뒤 순서로 배정")

    origin_xy = None
    if ("origin_check", None) in added:
        origin_xy = resolve_origin(conn, goal.get("origin"))
        if origin_xy is None:
            state.emit("origin_check", "code", "skip", f"출발지 '{goal.get('origin')}' 위치를 데이터에서 찾지 못해 미반영")

    itinerary = create_itinerary(general, slots, goal, settings, origin_xy, region_order(regions_cfg))
    state.emit("create_itinerary", "code", "ok",
               " / ".join(f"{d['day']}일차 {pmap[d['place_ids'][0]]['region_name'] if d['place_ids'] else '-'} {len(d['place_ids'])}곳"
                          for d in itinerary["days"]))
    if inject:
        itinerary, pid = inject_error(itinerary, scored, pmap, settings)
        if pid:
            state.emit("inject_error", "code", "add",
                       f"오류 주입 시연: 1일차에 {pmap[pid]['region_name']} 장소 '{pmap[pid]['name']}' 삽입")
    routes = calculate_route(itinerary, pmap)
    state.emit("calculate_route", "code", "ok", " / ".join(f"{r['day']}일차 직선 {r['total_km']} km" for r in routes))

    candidates_by_region = {}
    for p in general:
        candidates_by_region.setdefault(p["region_id"], []).append(p)
    for lst in slots.values():
        for p in lst:
            candidates_by_region.setdefault(p["region_id"], []).append(p)
    itinerary, remaining = revise_loop(conn, state, itinerary, pmap, candidates_by_region, goal, settings, llm,
                                       origin_xy=origin_xy)
    return assemble_result(conn, state, goal, itinerary, scored, remaining, settings, interests_cfg, llm)
