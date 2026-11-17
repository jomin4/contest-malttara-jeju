"""M8 타이핑 퀘스트 (설계 6.9)."""
import re

MAX_LABEL = 12


def quest_label(name: str) -> str:
    s = re.sub(r"\s*\(.*?\)\s*", " ", name or "").strip()
    s = re.sub(r"\s+", " ", s)
    if len(s.replace(" ", "")) <= MAX_LABEL:
        return s
    first = s.split(" ")[0]
    return first if len(first) <= MAX_LABEL else first[:MAX_LABEL]


def generate_quests(itinerary: dict, places: dict) -> list:
    return [{"day": d["day"], "items": [{"place_id": pid, "label": quest_label(places[pid]["name"])}
                                        for pid in d["place_ids"] if pid in places]}
            for d in itinerary["days"]]
