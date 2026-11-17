"""M8 설명 템플릿·인쇄용 HTML. 수치는 Tool 값만 슬롯에 넣는다.

원칙 3: 읍면동 지표는 읍면동 이름을 주어로 쓰고, 장소를 평가하는 문장("한적한 곳")을 만들지 않는다.
"""
import html

UNSET_LABELS = [("pace", "여유"), ("transport", "이동수단"), ("companion", "동행"), ("origin", "출발지"), ("month", "날짜")]


def _pct(p) -> int:
    return round(p * 100)


def explain_place(place: dict, goal: dict, interests_cfg: dict) -> list:
    lines = []
    cat = place.get("category")
    slot = place.get("slot")
    if slot:
        lines.append(f"TourAPI 등록 {'카페' if slot == '카페' else '음식점'} (관심사 '{slot}')")
    elif not cat:
        lines.append("분류 없음")
    elif not goal.get("interests"):
        lines.append(f"분류 '{cat}' · 관심사 미반영")
    else:
        hits = [k for k in goal["interests"] if cat in interests_cfg["interests"].get(k, {}).get("categories", [])]
        lines.append(f"관심사 '{hits[0]}' ↔ 분류 '{cat}' 일치" if hits else f"분류 '{cat}' · 입력한 관심사와 일치하지 않음")

    r = place["indicators"]["region"]
    if r["missing"]:
        lines.append(f"{r['emd'] or '읍면동 미상'} 지표 없음 (563)")
    else:
        when = f"{r['month']}월" if r.get("month") else "전체 기간 평균"
        lines.append(f"{r['emd']} 지표(읍면동 단위): 방문/거주 비율 {r['visit_ratio']:.2f}, 범위 내 백분위 {_pct(r['pct'])} "
                     f"({when}, 563 · {r['period']})")
    n = place["indicators"]["nearby"]
    if n["missing"]:
        lines.append(f"장소 반경 {n['radius_km']:g}km 지표 없음 (1208)")
    else:
        lines.append(f"장소 반경 {n['radius_km']:g}km 렌터카 체류 {n['quiet_count']}건, 범위 내 백분위 {_pct(n['pct'])} "
                     f"(1208 · {n['period']})")
    return lines


def unset_fields(goal: dict) -> list:
    out = []
    for key, label in UNSET_LABELS:
        if goal.get(key) is None:
            out.append("여유(보통 기준 적용)" if key == "pace" else label)
    return out


def summary_template(result: dict) -> str:
    places = result["places"]
    parts = []
    for d, r in zip(result["itinerary"]["days"], result["routes"]):
        rname = places[d["place_ids"][0]]["region_name"] if d["place_ids"] else "권역 없음"
        parts.append(f"{d['day']}일차 {rname} {len(d['place_ids'])}곳, 직선 {r['total_km']} km")
    text = " / ".join(parts) + "."
    unset = unset_fields(result["goal"])
    if unset:
        text += f" 미반영 조건: {', '.join(unset)}."
    if result["violations_remaining"]:
        text += f" 남은 검증 위반 {len(result['violations_remaining'])}건은 화면에서 확인해 주세요."
    return text


def export_travel_plan(result: dict, sources: list) -> str:
    e = html.escape
    places = result["places"]
    rows = []
    for d, r in zip(result["itinerary"]["days"], result["routes"]):
        rows.append(f"<h2>{d['day']}일차 · 직선 {r['total_km']} km (도로거리·이동시간 아님)</h2><ol>")
        for pid in d["place_ids"]:
            p = places[pid]
            why = "".join(f"<li>{e(s)}</li>" for s in result["explanations"].get(pid, []))
            rows.append(f"<li><b>{e(p['name'])}</b> <small>{e(p.get('category') or '분류 없음')}</small><ul>{why}</ul></li>")
        rows.append("</ol>")
    src = "".join(f"<tr><td>{e(str(s.get('source_id')))}</td><td>{e(str(s.get('name') or ''))}</td>"
                  f"<td>{e(str(s.get('period_actual') or ''))}</td></tr>" for s in sources)
    unset = ", ".join(unset_fields(result["goal"])) or "없음"
    return ("<!doctype html><html lang='ko'><head><meta charset='utf-8'><title>말따라 제주 여행 계획</title>"
            "<style>body{font-family:sans-serif;margin:24px;color:#131b2e}h1{color:#005c55}h2{font-size:18px;margin-top:20px}"
            "small{color:#3e4947}table{border-collapse:collapse}td{border:1px solid #bdc9c6;padding:4px 8px}"
            "@media print{button{display:none}}</style></head><body>"
            f"<h1>말따라 제주 여행 계획</h1><p>배치 {e(result['batch_id'])} · 미반영 조건: {e(unset)}</p>"
            f"<p>{e(result.get('summary') or '')}</p>{''.join(rows)}"
            f"<h2>데이터 출처</h2><table>{src}</table>"
            "<p><small>거리는 장소 사이 직선거리입니다. 지역 지표는 읍면동 단위 통계이며 개별 장소의 속성이 아닙니다.</small></p>"
            "<button onclick='window.print()'>인쇄</button></body></html>")
