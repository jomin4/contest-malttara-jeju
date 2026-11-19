"""189/190(내·외국인 관광지 입장객 수 추이) → 장소별 월 입장객(표준 라이브러리만).

관광지명 → place_id는 수작업표(data/mapping/sights_to_places.csv)를 먼저 쓰고,
그다음 정규화 이름 완전 일치만 쓴다(애매한 유사 매칭은 하지 않는다).
"""
import csv
import re

from malttara.etl.names import normalize_name, open_csv

SOURCE_ID = "189,190"
_SUFFIXES = ["관광지"]


def _sight_key(name: str, prefixes: list) -> str:
    s = normalize_name(name, prefixes)
    for suf in _SUFFIXES:
        if s.endswith(suf) and len(s) > len(suf):
            s = s[: -len(suf)]
    return s


def match_sights(sight_names: list, places: list, manual: dict, prefixes: list) -> dict:
    """{sight_name: place_id}. 수작업표 우선, 그다음 정규화 이름(접미 '관광지' 제거) 완전 일치.

    같은 정규화 이름의 장소가 여럿이면 모호하므로 자동 매칭하지 않는다(수작업표로 지정).
    """
    by_key = {}
    for p in places:
        by_key.setdefault(_sight_key(p.get("name", ""), prefixes), []).append(p)
    out = {}
    for name in sight_names:
        if name in manual:
            out[name] = manual[name]
            continue
        cands = by_key.get(_sight_key(name, prefixes), [])
        if len(cands) > 1:                      # 여럿이면 분류가 있는 기록이 하나일 때만 그것으로
            cands = [p for p in cands if p.get("category")]
        if len(cands) == 1:
            out[name] = cands[0]["place_id"]
    return out


def _year_month(v: str) -> "str | None":
    """'2009.01' / '200901' / '2009-01' → '2009-01'."""
    digits = re.sub(r"\D", "", v or "")
    if len(digits) < 6 or not 1 <= int(digits[4:6]) <= 12:
        return None
    return f"{digits[:4]}-{digits[4:6]}"


def _count(v) -> "int | None":
    s = str(v or "").replace(",", "").strip()
    if not s:
        return None
    try:
        return int(float(s))
    except ValueError:
        return None


def aggregate_sights(csv_paths: dict, mapping: dict) -> list:
    """csv_paths = {"domestic": 189경로, "foreign": 190경로} → place_id·연월별 입장객 행.

    출력 {place_id, year_month, domestic, foreign, source_id}. 한쪽 값이 없으면 None.
    관광지 여러 개가 같은 place_id로 매핑되면 더한다. place_id·연월 순으로 정렬.
    """
    acc = {}  # (place_id, ym) → {"domestic": n|None, "foreign": n|None}
    for kind in ("domestic", "foreign"):
        path = csv_paths.get(kind)
        if not path:
            continue
        with open_csv(path) as f:
            for row in csv.DictReader(f):
                pid = mapping.get((row.get("관광지명") or "").strip())
                ym = _year_month(row.get("날짜", ""))
                n = _count(row.get("관광객수"))
                if not pid or ym is None or n is None:
                    continue
                slot = acc.setdefault((pid, ym), {"domestic": None, "foreign": None})
                slot[kind] = (slot[kind] or 0) + n
    return [
        {"place_id": pid, "year_month": ym, "domestic": v["domestic"], "foreign": v["foreign"], "source_id": SOURCE_ID}
        for (pid, ym), v in sorted(acc.items())
    ]
