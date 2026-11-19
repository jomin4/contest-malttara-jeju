"""LLM 판단 지점 래퍼: LLM → 검증 → 실패하면 규칙. 결과는 agent_decisions에 남긴다(원칙 1·7)."""
import json
import re
from datetime import datetime

POLISH_SCHEMA = {"type": "object", "properties": {"text": {"type": "string"}},
                 "required": ["text"], "additionalProperties": False}
_NUM = re.compile(r"\d+(?:\.\d+)?")


def _record(conn, batch_id, point, actor, options, choice, reason):
    if conn is None:
        return
    conn.execute(
        "INSERT INTO agent_decisions(batch_id, point, actor, options_json, choice_json, reason, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?)",
        (batch_id, point, actor, json.dumps(options, ensure_ascii=False, default=str),
         json.dumps(choice, ensure_ascii=False, default=str), reason, datetime.now().isoformat(timespec="seconds")))
    conn.commit()


def decide(conn, batch_id, point, llm, system, user, schema, accept, fallback, options=None):
    """반환 (선택, 'llm'|'rule')."""
    reason = "llm_unavailable"
    if llm is not None and llm.available:
        out = llm.chat_json(system, user, schema)
        try:
            ok = out is not None and accept(out)
        except Exception:
            ok = False
        if ok:
            _record(conn, batch_id, point, "llm", options, out, "accepted")
            return out, "llm"
        status = getattr(llm, "last_status", None)
        reason = status if status in ("injection_suspected", "rate_limited") else "llm_invalid"
    choice = fallback()
    _record(conn, batch_id, point, "rule", options, choice, reason)
    return choice, "rule"


def polish_text(llm, template: str):
    """문장만 다듬는다. 템플릿에 없는 숫자가 생기면 템플릿을 그대로 쓴다."""
    if llm is None or not llm.available:
        return template, "rule"
    out = llm.chat_json(
        "너는 여행 일정 설명 문장을 자연스럽게 다듬는다. 숫자·장소명·데이터 출처는 바꾸거나 더하지 않는다.",
        template, POLISH_SCHEMA)
    if not out or not out.get("text"):
        return template, "rule"
    allowed = set(_NUM.findall(template))
    if any(n not in allowed for n in _NUM.findall(out["text"])):
        return template, "rule"
    return out["text"], "llm"
