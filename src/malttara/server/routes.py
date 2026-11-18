"""계약 API 핸들러(docs/superpowers/plans/2026-11-16-api-contract.md 2장).

각 핸들러는 (ctx, match, query, body) → (status, payload) 이고 payload가 dict면 JSON, str이면 HTML이다.
"""
import copy
import json
import re
import threading
from datetime import datetime

from malttara.agent.batch_a import GOAL_ERRORS, run_batch_a
from malttara.agent.batch_b import run_batch_b
from malttara.agent.decide import _record
from malttara.agent.prompts import GOAL_SYSTEM
from malttara.agent.state import BatchState
from malttara.db import connect, data_sources, meta_get
from malttara.tools.explain import export_travel_plan
from malttara.tools.feedback import record_event
from malttara.tools.goal import merge_goal, parse_goal_rules, validate_goal
from malttara.agent.pipeline import compact
from malttara.tools.places import analyze_tourism, get_region_data, get_region_data_all, score_places


class ApiError(Exception):
    def __init__(self, status: int, message: str):
        super().__init__(message)
        self.status, self.message = status, message


def require(body, spec: dict):
    if not isinstance(body, dict):
        raise ApiError(400, "요청 본문은 JSON 객체여야 합니다")
    for key, types in spec.items():
        if key not in body:
            raise ApiError(400, f"'{key}' 값이 없습니다")
        if not isinstance(body[key], types):
            raise ApiError(400, f"'{key}' 값의 형식이 올바르지 않습니다")


def goal_schema(interest_keys):
    s = lambda: {"type": ["string", "null"]}
    return {"type": "object", "required": ["days", "interests", "evidence"], "properties": {
        "nights": {"type": ["integer", "null"]}, "days": {"type": ["integer", "null"]},
        "pace": {"type": ["string", "null"]}, "interests": {"type": "array", "items": {"enum": list(interest_keys)}},
        "quiet_pref": {"type": "boolean"}, "transport": s(), "companion": s(), "origin": s(),
        "month": {"type": ["integer", "null"]},
        "evidence": {"type": "object", "additionalProperties": {"type": "string"}}}}


def h_health(ctx, m, q, body):
    with ctx.db() as conn:
        return 200, {"ok": True, "llm_available": ctx.llm.available, "data_version": meta_get(conn, "data_version")}


def h_config(ctx, m, q, body):
    return 200, {"interests": [{"key": k, "slot": bool(v.get("slot"))} for k, v in ctx.interests["interests"].items()],
                 "regions": [{"region_id": r["region_id"], "name": r["name"]} for r in ctx.regions["regions"]],
                 "max_days": ctx.settings["max_days"], "supports": ["places", "picks"]}


def h_parse(ctx, m, q, body):
    require(body, {"text": str})
    text = body["text"].strip()[:500]
    rule = parse_goal_rules(text, ctx.interests)
    goal, actor = rule, "rule"
    if ctx.llm.available and text:
        out = ctx.llm.chat_json(GOAL_SYSTEM + "\n관심사 키: " + ", ".join(ctx.interests["interests"]), text,
                                goal_schema(ctx.interests["interests"].keys()))
        goal, used = merge_goal(out, rule, text, ctx.interests)
        actor = "llm" if used else "rule"
        with ctx.db() as conn:
            _record(conn, "parse", "parse_goal", actor, {"text": text}, goal,
                    "accepted" if used else ("llm_invalid" if out is None else "no_change"))
    goal = copy.deepcopy(goal)
    missing = validate_goal(goal)
    return 200, {"goal": goal, "missing": missing, "actor": actor}


def h_map(ctx, m, q, body):
    if ctx.map_data is None:
        raise ApiError(404, "지도 데이터가 없습니다. 데이터 빌드(build_db)를 먼저 실행해 주세요")
    return 200, ctx.map_data


def h_stats(ctx, m, q, body):
    month = q.get("month")
    with ctx.db() as conn:
        if month == "all":
            return 200, get_region_data_all(conn, ctx.settings, ctx.regions)
        if month in (None, ""):
            return 200, get_region_data(conn, None, ctx.settings, ctx.regions)
        if not month.isdigit() or not 1 <= int(month) <= 12:
            raise ApiError(400, "month는 1~12 또는 all이어야 합니다")
        return 200, get_region_data(conn, int(month), ctx.settings, ctx.regions)


def _start(ctx, state, fn):
    ctx.batches[state.batch_id] = state

    def work():
        conn = connect(ctx.db_path)
        try:
            fn(conn)
        except Exception as e:  # 화면에 보여줄 한국어 문장으로
            state.emit("agent", "code", "fail", f"내부 오류: {type(e).__name__}")
            state.fail("경로를 만드는 중 오류가 났습니다. 다시 시도해 주세요")
        finally:
            if not state.done:
                state.fail(state.error or "경로를 만들지 못했습니다")
            conn.close()
    threading.Thread(target=work, daemon=True).start()
    return 200, {"batch_id": state.batch_id}


def h_batch_a(ctx, m, q, body):
    require(body, {"goal": dict})
    goal = copy.deepcopy(body["goal"])
    errs = validate_goal(goal)
    if errs:
        raise ApiError(400, GOAL_ERRORS.get(errs[0], "조건을 확인해 주세요"))
    inject = bool(body.get("inject_error"))
    st = BatchState("A")
    return _start(ctx, st, lambda conn: run_batch_a(conn, goal, inject, ctx.llm, ctx.settings, ctx.interests, ctx.regions, st))


def _stored(ctx, batch_id):
    st = ctx.batches.get(batch_id)
    if st is not None and st.done and st.result is not None:
        return st.result
    with ctx.db() as conn:
        row = conn.execute("SELECT result_json FROM batches WHERE batch_id = ?", (batch_id,)).fetchone()
    if row and row["result_json"] and row["result_json"] != "null":
        return json.loads(row["result_json"])
    return None


def h_batch_b(ctx, m, q, body):
    require(body, {"prev_batch_id": str})
    prev = body["prev_batch_id"]
    if _stored(ctx, prev) is None:
        raise ApiError(404, "이전 경로를 찾을 수 없습니다. 처음부터 다시 시작해 주세요")
    picks = body.get("picks") or []
    if not isinstance(picks, list) or len(picks) > MAX_PICKS or not all(
            isinstance(x, dict) and isinstance(x.get("place_id"), str)
            and (x.get("day") is None or (isinstance(x["day"], int) and not isinstance(x["day"], bool))) for x in picks):
        raise ApiError(400, f"picks는 [{{place_id, day}}] 목록이어야 합니다 (최대 {MAX_PICKS}곳)")
    st = BatchState("B", prev_batch_id=prev)
    return _start(ctx, st, lambda conn: run_batch_b(conn, prev, ctx.llm, ctx.settings, ctx.interests, ctx.regions, st,
                                                    picks=picks))


MAX_PICKS = 20
PLACE_SORTS = {
    "score": lambda p: (-p["score"], p["place_id"]),
    "quiet": lambda p: (-(p["spread"] + p["quiet"]), -p["score"], p["place_id"]),
    "name": lambda p: (p["name"], p["place_id"]),
}


def h_places(ctx, m, q, body):
    """직접 고르기 목록. DB를 매번 읽으므로 데이터 갱신이 바로 반영된다. batch_id를 주면 그 실행의 조건으로 점수를 매긴다."""
    goal = {}
    if q.get("batch_id"):
        res = _stored(ctx, q["batch_id"])
        if res is None:
            raise ApiError(404, "해당 실행 기록이 없습니다")
        goal = res.get("goal") or {}
    sort = q.get("sort") or "score"
    if sort not in PLACE_SORTS:
        raise ApiError(400, "sort는 score, quiet, name 중 하나입니다")
    try:
        limit = max(1, min(int(q.get("limit") or 40), 200))
        offset = max(0, int(q.get("offset") or 0))
    except ValueError:
        raise ApiError(400, "limit, offset은 정수여야 합니다")
    cats = None
    if q.get("interest"):
        spec = ctx.interests["interests"].get(q["interest"])
        if spec is None:
            raise ApiError(400, "알 수 없는 관심사입니다")
        cats = set(spec["categories"])
    text = (q.get("q") or "").replace(" ", "")
    region = q.get("region")
    with ctx.db() as conn:
        rows = score_places(conn, goal, ctx.settings, ctx.interests)
    rows = [p for p in rows if (not region or p["region_id"] == region) and (cats is None or p["category"] in cats)
            and (not text or text in p["name"].replace(" ", ""))]
    rows.sort(key=PLACE_SORTS[sort])
    return 200, {"total": len(rows), "offset": offset, "limit": limit, "sort": sort,
                 "items": [compact(p) for p in rows[offset:offset + limit]]}


def h_events_poll(ctx, m, q, body):
    bid = m.group(1)
    try:
        after = int(q.get("after") or 0)
    except ValueError:
        raise ApiError(400, "after는 정수여야 합니다")
    st = ctx.batches.get(bid)
    if st is None:
        res = _stored(ctx, bid)
        if res is None:
            raise ApiError(404, "해당 실행 기록이 없습니다")
        return 200, {"events": [], "done": True, "result": res, "error": None}
    return 200, {"events": st.events_after(after), "done": st.done,
                 "result": st.result if st.done else None, "error": st.error}


def h_post_event(ctx, m, q, body):
    require(body, {"batch_id": str, "place_id": str, "type": str})
    try:
        with ctx.db() as conn:
            record_event(conn, body["batch_id"], body["place_id"], body["type"], body.get("value"))
    except ValueError as e:
        raise ApiError(400, str(e))
    return 200, {"ok": True}


def h_trend(ctx, m, q, body):
    pid = m.group(1)
    with ctx.db() as conn:
        t = analyze_tourism(conn, [pid]).get(pid)
    return 200, t or {"place_id": pid, "period": None, "source_ids": ["189", "190"], "series": []}


def h_print(ctx, m, q, body):
    res = _stored(ctx, m.group(1))
    if res is None:
        raise ApiError(404, "해당 실행 기록이 없습니다")
    with ctx.db() as conn:
        return 200, export_travel_plan(res, data_sources(conn))


ROUTES = [
    ("GET", re.compile(r"^/api/health$"), h_health),
    ("GET", re.compile(r"^/api/config$"), h_config),
    ("POST", re.compile(r"^/api/goal/parse$"), h_parse),
    ("GET", re.compile(r"^/api/map$"), h_map),
    ("GET", re.compile(r"^/api/stats/emd$"), h_stats),
    ("POST", re.compile(r"^/api/batch/a$"), h_batch_a),
    ("POST", re.compile(r"^/api/batch/b$"), h_batch_b),
    ("GET", re.compile(r"^/api/batch/([A-Za-z0-9\-]+)/events$"), h_events_poll),
    ("POST", re.compile(r"^/api/events$"), h_post_event),
    ("GET", re.compile(r"^/api/places$"), h_places),
    ("GET", re.compile(r"^/api/places/([^/]+)/trend$"), h_trend),
    ("GET", re.compile(r"^/api/print/([A-Za-z0-9\-]+)$"), h_print),
]
