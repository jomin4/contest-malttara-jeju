"""배치 상태와 실행 로그(계약 LogEvent). 서버 폴링이 events_after(n)로 읽는다."""
import json
import threading
from datetime import datetime

_ISSUED = set()
_ISSUED_LOCK = threading.Lock()


def new_batch_id(kind: str, now: datetime) -> str:
    base = f"{kind}-{now:%m%d-%H%M%S}"
    with _ISSUED_LOCK:
        bid, n = base, 2
        while bid in _ISSUED:
            bid, n = f"{base}-{n}", n + 1
        _ISSUED.add(bid)
    return bid


class BatchState:
    def __init__(self, kind: str, now: datetime = None, prev_batch_id=None):
        self.kind = kind
        self.batch_id = new_batch_id(kind, now or datetime.now())
        self.prev_batch_id = prev_batch_id
        self.goal = None
        self.events = []
        self.done = False
        self.result = None
        self.error = None
        self._lock = threading.Lock()

    def emit(self, tool: str, actor: str, status: str, message: str) -> dict:
        with self._lock:
            ev = {"seq": len(self.events) + 1, "batch_id": self.batch_id, "tool": tool, "actor": actor,
                  "status": status, "message": message, "ts": datetime.now().isoformat(timespec="seconds")}
            self.events.append(ev)
            return ev

    def events_after(self, n: int) -> list:
        with self._lock:
            return [e for e in self.events if e["seq"] > n]

    def finish(self, result: dict) -> None:
        with self._lock:
            self.result, self.done = result, True

    def fail(self, error: str) -> None:
        with self._lock:
            self.error, self.done = error, True

    def save(self, conn) -> None:
        conn.execute(
            "INSERT OR REPLACE INTO batches(batch_id, kind, prev_batch_id, goal_json, result_json, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (self.batch_id, self.kind, self.prev_batch_id, json.dumps(self.goal, ensure_ascii=False),
             json.dumps(self.result, ensure_ascii=False), datetime.now().isoformat(timespec="seconds")))
        conn.commit()
