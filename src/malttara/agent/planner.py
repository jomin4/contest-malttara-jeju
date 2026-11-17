"""M2 작업 계획 (설계 6.3.1). 필수 단계는 코드가 고정하고, 여기서는 추가·생략할 Tool만 정한다."""
from malttara.agent.schema_lite import check_schema

PLAN_TOOLS = ("search_slot", "interest_filter", "get_region_data", "monthly_indicator",
              "origin_check", "analyze_tourism", "check_data_quality")

PLAN_SCHEMA = {
    "type": "object", "required": ["items"], "additionalProperties": False,
    "properties": {"items": {"type": "array", "items": {
        "type": "object", "required": ["tool", "action", "reason"], "additionalProperties": False,
        "properties": {
            "tool": {"enum": list(PLAN_TOOLS)},
            "action": {"enum": ["add", "skip"]},
            "reason": {"type": "string"},
            "params": {"type": "object", "additionalProperties": False,
                       "properties": {"slot": {"type": "string"}}},
        }}}},
}


def plan_tasks_rules(goal: dict, has_trend_candidates: bool, interests_cfg: dict = None) -> list:
    items = []
    slots = []
    if interests_cfg:
        slots = [k for k in goal.get("interests") or [] if interests_cfg["interests"].get(k, {}).get("slot")]
    else:
        slots = [k for k in goal.get("interests") or [] if k in ("음식", "카페")]
    for s in slots:
        items.append({"tool": "search_slot", "action": "add", "reason": f"관심사 '{s}' → 하루 1곳 {s} 탐색 추가",
                      "params": {"slot": s}})
    if goal.get("interests"):
        items.append({"tool": "interest_filter", "action": "add",
                      "reason": f"관심사 {', '.join(goal['interests'])} 분류 일치 장소 우선", "params": {}})
    else:
        items.append({"tool": "interest_filter", "action": "skip", "reason": "관심사 미반영 → 관심사 필터 생략", "params": {}})
    if goal.get("quiet_pref"):
        items.append({"tool": "get_region_data", "action": "add",
                      "reason": "한적함 요청 → 읍면동 방문 집중도 비교 추가, 분산·한적함 가중치 상향", "params": {}})
    else:
        items.append({"tool": "get_region_data", "action": "skip",
                      "reason": "한적함 요청 없음 → 권역 비교는 점수 안에서만 반영", "params": {}})
    if goal.get("month"):
        items.append({"tool": "monthly_indicator", "action": "add",
                      "reason": f"{goal['month']}월 입력 → 해당 월 읍면동 지표 사용", "params": {}})
    else:
        items.append({"tool": "monthly_indicator", "action": "skip", "reason": "날짜 미반영 → 전체 기간 평균 지표 사용", "params": {}})
    if goal.get("origin"):
        items.append({"tool": "origin_check", "action": "add", "reason": "출발지 입력 → 출발지 거리 검증 추가", "params": {}})
    else:
        items.append({"tool": "origin_check", "action": "skip", "reason": "출발지 미반영 → 출발지 거리 검증 생략", "params": {}})
    if has_trend_candidates:
        items.append({"tool": "analyze_tourism", "action": "add", "reason": "입장객 통계(189·190)가 있는 후보 → 추이 분석 추가", "params": {}})
    else:
        items.append({"tool": "analyze_tourism", "action": "skip", "reason": "입장객 통계가 있는 후보 없음 → 생략", "params": {}})
    items.append({"tool": "check_data_quality", "action": "add", "reason": "분류·지표 누락 현황 확인", "params": {}})
    return items


def accept_plan(out: dict) -> bool:
    return isinstance(out, dict) and check_schema(out, PLAN_SCHEMA) and bool(out["items"])


def enforce_required(items: list, goal: dict, interests_cfg: dict, has_trend: bool) -> list:
    """LLM 계획이어도 사실과 어긋나는 항목은 코드가 바로잡는다(요청한 slot 탐색, 출발지 없음 등)."""
    rule = {(i["tool"], (i.get("params") or {}).get("slot")): i for i in plan_tasks_rules(goal, has_trend, interests_cfg)}
    out = {}
    for i in items:
        key = (i["tool"], (i.get("params") or {}).get("slot"))
        out[key] = i
    for key, ri in rule.items():
        cur = out.get(key)
        must_match = key[0] in ("search_slot", "origin_check", "monthly_indicator", "analyze_tourism")
        if cur is None or (must_match and cur["action"] != ri["action"]):
            out[key] = ri
    return list(out.values())
