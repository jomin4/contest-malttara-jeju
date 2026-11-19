"""LLM 토큰 사용량·비용 기록(비용을 신경 쓴 설계의 실측 근거).

판단 지점마다 실제로 쓴 입력·출력 토큰을 llm_usage 표(db.py)에 남기고, 단가(config/settings.json
llm.price_usd_per_mtok)로 비용을 계산한다. 단가가 없는 모델은 비용을 None으로 둔다(지어내지 않는다).

    PYTHONPATH=src python -m malttara.agent.usage [DB 경로]   # 배치별·판단 지점별 집계 출력
"""
import json
import sys
from datetime import datetime


def record_usage(conn, batch_id, point, llm) -> None:
    take = getattr(llm, "take_usage", None)
    usage = take() if take else None
    if conn is None or not usage:
        return
    conn.execute("INSERT INTO llm_usage(batch_id, point, model, input_tokens, output_tokens, created_at) "
                 "VALUES (?, ?, ?, ?, ?, ?)",
                 (batch_id, point, usage["model"], usage["input_tokens"], usage["output_tokens"],
                  datetime.now().isoformat(timespec="seconds")))
    conn.commit()


def _usd(model, inp, out, prices):
    p = prices.get(model)
    if not p:
        return None
    return inp / 1_000_000 * p["input"] + out / 1_000_000 * p["output"]


def usage_summary(conn, settings) -> dict:
    """{calls, input_tokens, output_tokens, usd, by_batch: {batch_id: {...}}, by_point: {point: {...}}}"""
    prices = settings["llm"].get("price_usd_per_mtok", {})
    rows = conn.execute("SELECT batch_id, point, model, input_tokens, output_tokens FROM llm_usage").fetchall()

    def empty():
        return {"calls": 0, "input_tokens": 0, "output_tokens": 0, "usd": 0.0}

    total, by_batch, by_point = empty(), {}, {}
    for batch_id, point, model, inp, out in rows:
        cost = _usd(model, inp, out, prices)
        for acc in (total, by_batch.setdefault(batch_id, empty()), by_point.setdefault(point, empty())):
            acc["calls"] += 1
            acc["input_tokens"] += inp
            acc["output_tokens"] += out
            acc["usd"] = None if cost is None or acc["usd"] is None else acc["usd"] + cost
    total["by_batch"], total["by_point"] = by_batch, by_point
    return total


def main(argv) -> int:
    from malttara.config import ROOT, load_config
    from malttara.db import connect
    path = argv[1] if len(argv) > 1 else str(ROOT / "data" / "db" / "malttara.sqlite")
    conn = connect(path)
    s = usage_summary(conn, load_config("settings"))
    conn.close()
    print(json.dumps(s, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
