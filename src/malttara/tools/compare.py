"""M7 경로 Diff (계약 DiffItem)."""


def compare_itineraries(prev: dict, new: dict, fb: dict, replaced: dict, added: dict, picked=frozenset()) -> list:
    """replaced: {이전 place_id: 새 place_id}, added: {새 place_id: 분류(이유용)}."""
    new_day = {pid: d["day"] for d in new["days"] for pid in d["place_ids"]}
    out = []
    for d in prev["days"]:
        for pid in d["place_ids"]:
            if pid in new_day:
                pin = pid in fb["pinned"]
                out.append({"place_id": pid, "change": "pin" if pin else "keep", "replaced_by": None,
                            "day": new_day[pid], "reason": "꼭 갈래요 → 고정" if pin else "유지"})
            elif pid in replaced:
                why = ("별로예요 → 같은 권역 대안으로 교체" if pid in fb["disliked"] else
                       "직접 고른 장소로 교체" if replaced[pid] in picked else "검증 위반 → 같은 권역 대안으로 교체")
                out.append({"place_id": pid, "change": "replace", "replaced_by": replaced[pid], "day": d["day"], "reason": why})
            else:
                out.append({"place_id": pid, "change": "remove", "replaced_by": None, "day": d["day"],
                            "reason": "별로예요 → 대안이 없어 제외" if pid in fb["disliked"] else "제외"})
    prev_ids = {pid for d in prev["days"] for pid in d["place_ids"]}
    repl_targets = set(replaced.values())
    for d in new["days"]:
        for pid in d["place_ids"]:
            if pid in prev_ids or pid in repl_targets:
                continue
            cat = added.get(pid)
            liked = cat and cat in fb.get("liked_categories", {})
            out.append({"place_id": pid, "change": "add", "replaced_by": None, "day": d["day"],
                        "reason": "직접 고름 → 추가" if pid in picked else f"관심 분류 '{cat}' 선호 → 추가" if liked else "빈자리 보충"})
    return out
