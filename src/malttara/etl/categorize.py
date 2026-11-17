"""장소 분류 매칭: 참조 데이터(TourAPI·허브 API·파일)와 이름·좌표로 맞춘다(설계 5.4-2)."""
from malttara.geo import haversine_km
from malttara.etl.names import name_similarity, normalize_name


def _coord(ref: dict) -> "tuple[float, float] | None":
    try:
        lat, lon = ref.get("lat"), ref.get("lon")
        if lat is None or lon is None or lat == "" or lon == "":
            return None
        return float(lat), float(lon)
    except (TypeError, ValueError):
        return None


def _prepare(refs: list, prefixes: list) -> list:
    """ref마다 (ref, 정규화 이름, 좌표 또는 None)을 미리 계산한다(대량 매칭 속도용)."""
    return [(ref, normalize_name(ref.get("name", ""), prefixes), _coord(ref)) for ref in refs]


def _match_prepared(place: dict, prepared: list, match_cfg: dict, prefixes: list) -> "dict | None":
    exact_km = match_cfg["exact_max_m"] / 1000.0
    fuzzy_km = match_cfg["fuzzy_max_m"] / 1000.0
    min_sim = match_cfg["fuzzy_min_sim"]
    max_deg = max(exact_km, fuzzy_km) / 100.0  # 위도 1° ≈ 111km → 넉넉한 사전 필터
    name = place.get("name", "")
    key = normalize_name(name, prefixes)
    plat, plon = float(place["lat"]), float(place["lon"])

    best_exact, best_fuzzy, no_coord_exact = None, None, None
    for ref, ref_key, c in prepared:
        same = bool(key) and ref_key == key
        if c is None:
            if same and no_coord_exact is None:
                no_coord_exact = ref
            continue
        if abs(c[0] - plat) > max_deg or abs(c[1] - plon) > max_deg * 1.3:
            continue
        d = haversine_km(plat, plon, c[0], c[1])
        if same and d <= exact_km:
            if best_exact is None or d < best_exact[0]:
                best_exact = (d, ref)
        elif d <= fuzzy_km and name_similarity(name, ref.get("name", "")) >= min_sim:
            if best_fuzzy is None or d < best_fuzzy[0]:
                best_fuzzy = (d, ref)
    if best_exact:
        return best_exact[1]
    if best_fuzzy:
        return best_fuzzy[1]
    return no_coord_exact


def match_reference(place: dict, refs: list, match_cfg: dict, prefixes: list) -> "dict | None":
    """place와 맞는 ref 하나를 돌려준다. 없으면 None.

    1) 정규화 이름이 같고 exact_max_m 이내 → 그중 가장 가까운 것
    2) 아니면 fuzzy_max_m 이내이면서 이름 유사도 ≥ fuzzy_min_sim 인 것 중 가장 가까운 것
    좌표 없는 ref(784 해수욕장 정보 등)는 정규화 이름 완전 일치만 본다.
    """
    return _match_prepared(place, _prepare(refs, prefixes), match_cfg, prefixes)


def _keyword_category(name: str, keyword_categories: dict) -> "str | None":
    """이름에 키워드가 들어 있으면 그 분류. 긴 키워드부터 본다(예: '숲길' > '숲')."""
    for kw in sorted(keyword_categories, key=len, reverse=True):
        if kw in (name or ""):
            return keyword_categories[kw]
    return None


def categorize_places(places: list, ref_sets: list, cfg: dict) -> dict:
    """places를 제자리 수정해 category·category_source·overview를 채우고 source별 건수를 돌려준다.

    ref_sets 순서대로 먼저 매칭된 것을 쓴다. overview는 tourapi에서만 받는다.
    어디에도 없으면 keyword_categories 부분 문자열 규칙("keyword"), 그것도 없으면 category=None("none").
    """
    prefixes = cfg.get("name_prefixes", [])
    counts = {name: 0 for name, _ in ref_sets}
    counts["keyword"] = 0
    counts["none"] = 0
    prepared = [(source, _prepare(refs, prefixes)) for source, refs in ref_sets]
    for p in places:
        p["overview"] = None
        matched = False
        for source, prep in prepared:
            ref = _match_prepared(p, prep, cfg["match"], prefixes) if prep else None
            if ref is not None:
                p["category"] = ref.get("category")
                p["category_source"] = source
                if source == "tourapi":
                    p["overview"] = ref.get("overview")
                counts[source] += 1
                matched = True
                break
        if matched:
            continue
        cat = _keyword_category(p.get("name", ""), cfg.get("keyword_categories", {}))
        if cat:
            p["category"], p["category_source"] = cat, "keyword"
            counts["keyword"] += 1
        else:
            p["category"], p["category_source"] = None, "none"
            counts["none"] += 1
    return counts
