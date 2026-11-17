"""M1 목표 해석(규칙)·검증·LLM 결과 병합.

원칙 2: 입력에 없는 조건은 None(미반영)으로 둔다. 기본값으로 채우지 않는다.
"""
import re

PACES = ("여유롭게", "보통", "빡빡하게")
TRANSPORTS = ("렌터카", "버스", "도보")
MAX_DAYS = 7

_PACE_RULES = [(r"빡빡|알차게|최대한\s*많이", "빡빡하게"), (r"여유|천천히|느긋", "여유롭게"), (r"보통", "보통")]
_TRANSPORT_RULES = [(r"렌터카|렌트|차로|자동차|자차", "렌터카"), (r"버스|대중교통", "버스"), (r"걸어|도보|뚜벅", "도보")]
_COMPANION_RULES = [(r"아이|아기|자녀|애들", "아이와 함께"), (r"부모님", "부모님과 함께"), (r"혼자|나홀로", "혼자"),
                    (r"친구", "친구와 함께"), (r"연인|커플|애인", "연인과 함께"), (r"가족", "가족과 함께")]


def empty_goal() -> dict:
    return {"nights": None, "days": None, "pace": None, "interests": [], "quiet_pref": False,
            "transport": None, "companion": None, "origin": None, "month": None, "evidence": {}}


def _first(rules, text):
    for pattern, value in rules:
        m = re.search(pattern, text)
        if m:
            return value, m.group(0)
    return None, None


def parse_goal_rules(text: str, interests_cfg: dict) -> dict:
    g = empty_goal()
    ev = g["evidence"]
    t = text or ""

    m = re.search(r"(\d+)\s*박\s*(\d+)\s*일", t)
    if m:
        g["nights"], g["days"] = int(m.group(1)), int(m.group(2))
        ev["days"] = m.group(0)
    elif re.search(r"당일", t):
        g["nights"], g["days"] = 0, 1
        ev["days"] = "당일"
    else:
        for m in re.finditer(r"(\d+)\s*일", t):
            if re.search(r"월\s*$", t[:m.start()]):      # "11월 20일" 같은 날짜는 기간이 아니다
                continue
            g["days"] = int(m.group(1))
            g["nights"] = g["days"] - 1
            ev["days"] = m.group(0)
            break

    g["pace"], ev_pace = _first(_PACE_RULES, t)
    if ev_pace:
        ev["pace"] = ev_pace

    hits = []
    for key, spec in interests_cfg["interests"].items():
        found = [w for w in spec["triggers"] if w in t]
        if found:
            g["interests"].append(key)
            hits.extend(found)
    if hits:
        ev["interests"] = ", ".join(hits)

    quiet = [w for w in interests_cfg.get("quiet_triggers", []) if w in t]
    g["quiet_pref"] = bool(quiet)
    if quiet:
        ev["quiet_pref"] = ", ".join(quiet)

    g["transport"], ev_tr = _first(_TRANSPORT_RULES, t)
    if ev_tr:
        ev["transport"] = ev_tr
    g["companion"], ev_co = _first(_COMPANION_RULES, t)
    if ev_co:
        ev["companion"] = ev_co

    m = re.search(r"(\d{1,2})\s*월", t)
    if m and 1 <= int(m.group(1)) <= 12:
        g["month"] = int(m.group(1))
        ev["month"] = m.group(0)

    m = re.search(r"([^\s,.]+?)(?:\s*근처)?에서\s*출발", t) or re.search(r"숙소(?:는|가)\s*([^\s,.]+?)(?:이고|이에요|예요|입니다|에|$|[\s,.])", t)
    if m:
        g["origin"] = m.group(1)
        ev["origin"] = m.group(1)
    return g


def validate_goal(goal: dict) -> list:
    """누락·범위 오류 코드 목록. nights는 days−1로 맞춘다(오류 아님)."""
    days = goal.get("days")
    if days is None:
        return ["days"]
    if not isinstance(days, int) or days < 1 or days > MAX_DAYS:
        return ["days_range"]
    goal["nights"] = days - 1
    return []


def _founded(value, field, llm_goal, text) -> bool:
    ev = (llm_goal.get("evidence") or {}).get(field)
    return bool(ev) and isinstance(ev, str) and ev in text and (not isinstance(value, str) or value in text or field != "origin")


def merge_goal(llm_goal, rule_goal: dict, text: str, interests_cfg: dict):
    """LLM 값은 원문에 근거(evidence가 원문 안에 있음)가 있을 때만 채택한다. 반환 (goal, LLM 값 채택 여부)."""
    if not llm_goal:
        return rule_goal, False
    merged = dict(rule_goal)
    merged["evidence"] = dict(rule_goal.get("evidence") or {})
    used = False
    allowed = {
        "pace": lambda v: v in PACES,
        "transport": lambda v: v in TRANSPORTS,
        "companion": lambda v: isinstance(v, str) and 0 < len(v) <= 20,
        "origin": lambda v: isinstance(v, str) and 0 < len(v) <= 30,
        "month": lambda v: isinstance(v, int) and 1 <= v <= 12,
        "days": lambda v: isinstance(v, int) and 1 <= v <= 30,
        "quiet_pref": lambda v: isinstance(v, bool),
    }
    for field, ok in allowed.items():
        v = llm_goal.get(field)
        if v is None or v == rule_goal.get(field) or not ok(v):
            continue
        if _founded(v, field, llm_goal, text):
            merged[field] = v
            merged["evidence"][field] = llm_goal["evidence"][field]
            used = True
    if merged.get("days") is not None:
        merged["nights"] = merged["days"] - 1
    keys = list(interests_cfg["interests"].keys())
    llm_int = [k for k in (llm_goal.get("interests") or []) if k in keys]
    union = [k for k in keys if k in rule_goal.get("interests", []) or k in llm_int]
    if union != list(rule_goal.get("interests", [])):
        used = True
    merged["interests"] = union
    return merged, used
