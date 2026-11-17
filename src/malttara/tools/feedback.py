"""M7 사용자 이벤트 저장·피드백 집계. 가상 도착과 실제 방문은 type으로 따로 저장한다(원칙 5)."""
from datetime import datetime

EVENT_TYPES = ("virtual_arrival", "feedback", "itinerary_add", "visited")
FEEDBACK_VALUES = ("interest", "must", "dislike")


def record_event(conn, batch_id: str, place_id: str, type: str, value) -> None:
    if type not in EVENT_TYPES:
        raise ValueError(f"알 수 없는 이벤트 종류: {type}")
    if type == "feedback" and value not in FEEDBACK_VALUES:
        raise ValueError(f"알 수 없는 반응: {value}")
    conn.execute("INSERT INTO user_interactions(batch_id, place_id, type, value, created_at) VALUES (?, ?, ?, ?, ?)",
                 (batch_id, place_id, type, value, datetime.now().isoformat(timespec="seconds")))
    conn.commit()


def load_events(conn, batch_id: str) -> list:
    rows = conn.execute("SELECT place_id, type, value FROM user_interactions WHERE batch_id = ? ORDER BY id",
                        (batch_id,)).fetchall()
    return [dict(r) for r in rows]


def analyze_feedback(events: list, places: dict) -> dict:
    last = {}
    arrived = set()
    for e in events:
        if e["type"] == "feedback":
            last[e["place_id"]] = e["value"]
        elif e["type"] == "virtual_arrival":
            arrived.add(e["place_id"])
    liked = {}
    for pid, v in last.items():
        if v in ("interest", "must"):
            cat = (places.get(pid) or {}).get("category")
            if cat:
                liked[cat] = liked.get(cat, 0) + 1
    return {"pinned": {p for p, v in last.items() if v == "must"},
            "disliked": {p for p, v in last.items() if v == "dislike"},
            "liked_categories": liked, "arrived": arrived}
