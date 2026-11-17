"""catalog_raw.json → data/catalog/* 색인 + data/cards/*.md 데이터 카드

사용법 (data/ 폴더 기준):
    python scripts/build_catalog.py

- 입력: catalog/catalog_raw.json (scripts/fetch_catalog.py 결과)
- 출력: catalog/INDEX.md, catalog/by-category/*.md, catalog/by-theme/, catalog/by-attribute/,
        catalog/join-keys/, catalog/series.md, catalog/catalog.jsonl, cards/*.md
- 카드의 <!-- notes:start --> ~ <!-- notes:end --> 안의 메모와 '분석 결과' 섹션, frontmatter의
  status / period_actual 값은 다시 생성해도 유지된다.
- 공간·시간 단위와 연결 키는 컬럼명으로 추정한 값이다 (guides/methodology.md 참고).
"""
import collections
import json
import os
import re
from pathlib import Path

DATA = Path(__file__).resolve().parent.parent
SRC = DATA / "catalog" / "catalog_raw.json"
CAT_DIR = DATA / "catalog"
CARD_DIR = DATA / "cards"
COLLECTED_AT = "2026-11-15"

# ----------------------------------------------------------------- helpers

def clean_title(t):
    return re.sub(r"^\[[^\]]+\]\s*", "", t or "").strip()


def slug(s, n=40):
    s = re.sub(r"[\\/:*?\"<>|\[\]\(\)#%&{}$!'@+`=,;~^]", " ", s)
    s = re.sub(r"\s+", "-", s.strip())
    return s[:n].strip("-.")


def header_of(x):
    p = x.get("preview")
    if isinstance(p, list) and p and isinstance(p[0], list):
        return [str(c).replace("\ufeff", "").strip() for c in p[0] if str(c).strip()]
    return []


def api_fields(x, kind):
    if not x.get("api"):
        return []
    return [e for e in x["api"]["el"] if e[0] == kind]


def colnames_text(x):
    parts = header_of(x)
    parts += [f"{e[1]} {e[2] or ''}" for e in api_fields(x, "response")]
    parts += [f"{e[1]} {e[2] or ''}" for e in api_fields(x, "request")]
    return " | ".join(parts)


def ftype(x):
    t = []
    if x.get("api"):
        t.append("API")
    if x.get("files"):
        t.append("파일")
    if x.get("link"):
        t.append("링크")
    return "+".join(t) or "없음"


def end_year(x):
    e = (x.get("end") or "")[:4]
    if e == "9999":
        return "계속(미정)"
    return e or "미기재"


SPATIAL_RULES = [
    ("좌표", r"위도|경도|latitude|longitude|\blat\b|\blng\b|좌표"),
    ("격자", r"격자|grid"),
    ("읍면동", r"읍면동|행정동|법정동|\bemd|emd_|동명|읍면"),
    ("정류소", r"정류소|정류장|station"),
    ("관광지", r"관광지명|sightsName|관광지"),
    ("시군구", r"시군구|행정시|sigungu|\bcity\b"),
    ("시도", r"시도|\bsido\b"),
]


def spatial_unit(x):
    t = colnames_text(x) + " " + x.get("title", "")
    for name, pat in SPATIAL_RULES:
        if re.search(pat, t, re.I):
            return name
    return ""


def temporal_unit(x):
    if x.get("auto") and x.get("period"):
        return x["period"]
    t = re.sub(r"데이터\s*기준\s*일자|기준일자|등록\s*일시|수정\s*일시|등록일|인증시작일|인증종료일", " ", colnames_text(x))
    rules = [
        ("시간", r"시간대|base_hour|시각|time_range"),
        ("일", r"일자|날짜|통계일|기준일|base_date|baseDate|searchDate|일별|\bdate\b"),
        ("월", r"년월|연월|월별|yearmonth|YearMonth|기준월|YYYYMM"),
        ("분기", r"분기|quarter"),
        ("연", r"연도|년도|기준 연도|baseYear|해당연도|연별|구분연도"),
    ]
    for name, pat in rules:
        if re.search(pat, t, re.I):
            return name
    return "시점(스냅샷)"


JOIN_RULES = [
    ("날짜(일)", r"base_date|baseDate|searchDate|기준일(?!자)|일자(?!.*데이터기준)|날짜|통계일|startDate"),
    ("연월", r"년월|연월|yearmonth|YearMonth|base_year_month|YYYYMM|dtYearMonth"),
    ("연도", r"연도|년도|baseYear|해당연도"),
    ("읍면동", r"읍면동|행정동|법정동|\bemd|emd_"),
    ("시군구", r"시군구|행정시|sigungu"),
    ("정류소", r"정류소|정류장|station"),
    ("노선", r"노선|route"),
    ("관광지명", r"관광지명|sightsName"),
    ("좌표", r"위도|경도|latitude|longitude"),
    ("주소", r"도로명|지번|주소|address"),
    ("업종", r"업종|marketType|biz"),
    ("국가", r"국가|국적|nationality"),
    ("품종·품목", r"품종|품목|cultivar"),
    ("성별·연령", r"성별|연령|gender|ageGroup|age_range"),
]


def join_keys(x):
    t = re.sub(r"데이터\s*기준\s*일자", " ", colnames_text(x))
    return [name for name, pat in JOIN_RULES if re.search(pat, t, re.I)]


THEMES = [
    ("대중교통·버스", r"버스|정류소|노선|대중교통"),
    ("교통·도로·안전", r"교통사고|도로|교통량|주차|CCTV|신호|자전거|렌터카|카셰어링"),
    ("전기차·모빌리티", r"전기차|전기자동차|충전소|충전 이력|이륜차|모빌리티|\bEV\b"),
    ("유동인구·인구", r"유동인구|인구|체류|출산|다문화|귀농|가구"),
    ("관광 수요·방문객", r"입도객|관광객|입장객|관람객|유입자|방문객|검색어|여행장소"),
    ("관광 장소·코스", r"관광지|오름|올레|둘레길|해수욕장|박물관|미술관|캠핑|명소|코스|휴양"),
    ("무장애·교통약자", r"무장애|장애인|휠체어|교통약자|이동약자"),
    ("소비·카드·상권", r"카드|소비|매출|상권|업종|가맹점|전통시장|포스|물가"),
    ("숙박·음식점", r"숙박|민박|음식점|식당|카페|휴게음식"),
    ("의료·복지·생활시설", r"병원|의원|약국|보건|복지|어린이집|노인|경로|도서관|산후조리"),
    ("환경·기상", r"기상|날씨|기온|강수|대기|미세먼지|소음|수질|용천수|곶자왈|생태"),
    ("폐기물·자원순환", r"폐기물|쓰레기|클린하우스|재활용|종량제|소각"),
    ("농축수산", r"감귤|농산물|채소|과수|축산|가축|수산|어업|양식|화훼|농가|농업"),
    ("통신·와이파이", r"와이파이|[Ww]i-?[Ff]i|공공\s*AP|AP\s*그룹|\bAP\b(?!I)"),
    ("경제·고용·산업", r"고용|실업|경기|기업|창업|사업체|산업|세금|지방세"),
    ("교육·행정", r"학교|교육|학생|행정|공공기관|위원회|민원"),
]


def themes_of(x):
    t = " ".join([x.get("title", ""), x.get("tag") or "", (x.get("desc") or "")[:200]])
    return [name for name, pat in THEMES if re.search(pat, t)]


SERIES_RULES = [
    ("무장애여행 위치정보", r"_무장애여행위치정보$", "장소별 이동 경로 포인트(위도·경도·경사·단차 등)"),
    ("무장애여행 주변정보", r"_무장애여행주변정보$", "장소 주변 음식점·카페·숙박의 휠체어 진입·장애인 화장실 여부"),
    ("무장애여행 일반정보", r"_무장애여행일반정보$", "장소 개요·편의시설"),
    ("제주 빅데이터 분석 주제 매쉬업 (주제1~10)", r"_주제\d+_", "제주도가 정한 분석 주제별로 여러 원천을 결합한 데이터"),
    ("렌터카 체류 빈도 (50m 격자)", r"렌터카 체류 빈도", "반기별 50m 격자 렌터카 체류 빈도"),
]


def series_of(title):
    for name, pat, _ in SERIES_RULES:
        if re.search(pat, title):
            return name
    return ""


def md_table(header, rows):
    def esc(v):
        return str("" if v is None else v).replace("|", "\\|").replace("\n", " ").strip()
    out = ["| " + " | ".join(esc(h) for h in header) + " |", "|" + "---|" * len(header)]
    out += ["| " + " | ".join(esc(v) for v in r) + " |" for r in rows]
    return "\n".join(out)


def yaml_val(v):
    if isinstance(v, list):
        return "[" + ", ".join(json.dumps(i, ensure_ascii=False) for i in v) + "]"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if v is None or v == "":
        return '""'
    return json.dumps(v, ensure_ascii=False)


# ----------------------------------------------------------------- build records

raw = json.load(open(SRC, encoding="utf-8"))
recs = []
for x in raw:
    title = clean_title(x["title"])
    x2 = dict(x, title=title)
    files = x.get("files") or []
    size_mb = round(sum(f[1] or 0 for f in files) / 1e6, 2)
    rec = {
        "id": x["id"],
        "title": title,
        "category": x["cat"],
        "type": ftype(x),
        "period_meta": f"{x.get('start') or ''} ~ {x.get('end') or ''}".strip(),
        "end_year": end_year(x),
        "auto_update": bool(x.get("auto")),
        "update_cycle": x.get("period") or "",
        "spatial": spatial_unit(x2),
        "temporal": temporal_unit(x2),
        "join_keys": join_keys(x2),
        "themes": themes_of(x2),
        "series": series_of(title),
        "owner": x.get("owner") or "",
        "tags": [t for t in re.split(r"\s+", (x.get("tag") or "").strip()) if t],
        "views": x.get("views") or 0,
        "favorites": x.get("fav") or 0,
        "created": x.get("created") or "",
        "updated": x.get("updated") or "",
        "file_count": len(files),
        "file_size_mb": size_mb,
        "file_formats": sorted({f[0].rsplit(".", 1)[-1].lower() for f in files if "." in f[0]}),
        "api_data_key": x["key"] if x.get("api") else "",
        "api_quota_per_day": x["api"]["quota"] if x.get("api") else None,
        "link": x.get("link") or "",
        "columns": header_of(x) or [e[1] for e in api_fields(x, "response")],
        "url": f"https://jejudatahub.net/data/view/data/{x['id']}",
        "summary": re.sub(r"\s+", " ", x.get("desc") or "").strip()[:160],
    }
    rec["card"] = f"cards/{x['id']:04d}_{slug(title)}.md"
    recs.append((rec, x))

recs.sort(key=lambda p: p[0]["id"])
REC = {r["id"]: r for r, _ in recs}

# ----------------------------------------------------------------- cards

CARD_DIR.mkdir(parents=True, exist_ok=True)
existing = {}
for p in CARD_DIR.glob("*.md"):
    m = re.match(r"^(\d{4})_", p.name)
    if m:
        existing[int(m.group(1))] = p.read_text(encoding="utf-8")

NOTES_DEFAULT = "<!-- notes:start -->\n(메모 없음)\n<!-- notes:end -->"
ANALYSIS_DEFAULT = "원본 미적재 (status: meta-only). 원본 수집·적재 후 scripts/profile.py가 행 수, 실제 기간, 결측, 상위 값을 채운다."


def keep_from(old, x_id):
    keep = {"notes": NOTES_DEFAULT, "analysis": ANALYSIS_DEFAULT, "status": "meta-only", "period_actual": ""}
    if not old:
        return keep
    m = re.search(r"<!-- notes:start -->.*?<!-- notes:end -->", old, re.S)
    if m:
        keep["notes"] = m.group(0)
    m = re.search(r"## 분석 결과\n\n(.*?)\n\n## 메모", old, re.S)
    if m:
        keep["analysis"] = m.group(1).strip()
    m = re.search(r"^status: \"?([\w-]+)\"?", old, re.M)
    if m:
        keep["status"] = m.group(1)
    m = re.search(r"^period_actual: (.*)$", old, re.M)
    if m:
        v = m.group(1).strip()
        keep["period_actual"] = "" if v in ('""', "") else json.loads(v) if v.startswith('"') else v
    return keep


written = set()
for rec, x in recs:
    k = keep_from(existing.get(rec["id"]), rec["id"])
    fm = {
        "id": rec["id"], "title": rec["title"], "category": rec["category"], "type": rec["type"],
        "period_meta": rec["period_meta"], "period_actual": k["period_actual"],
        "auto_update": rec["auto_update"], "update_cycle": rec["update_cycle"],
        "spatial": rec["spatial"], "temporal": rec["temporal"], "join_keys": rec["join_keys"],
        "themes": rec["themes"], "series": rec["series"], "owner": rec["owner"],
        "status": k["status"], "url": rec["url"],
    }
    L = ["---"] + [f"{key}: {yaml_val(v)}" for key, v in fm.items()] + ["---", "", f"# {rec['title']}", ""]

    # 요약
    unit = " · ".join(u for u in [rec["spatial"] and f"공간 {rec['spatial']}", f"시간 {rec['temporal']}"] if u)
    L += ["## 요약", "", f"- {rec['category']} 분야, 제공형태 **{rec['type']}**, 수집기간(메타) {rec['period_meta']}",
          f"- 단위(추정): {unit}" + (f" / 연결 키(추정): {', '.join(rec['join_keys'])}" if rec["join_keys"] else ""),
          f"- 제공처: {rec['owner']} / 조회수 {rec['views']} / 등록 {rec['created']} · 수정 {rec['updated']}"]
    if rec["tags"]:
        L.append(f"- 태그: {' '.join(rec['tags'])}")
    L += ["", "### 원문 설명", "", (x.get("desc") or "").strip() or "-", ""]

    # 수집 방법
    L += ["## 수집 방법", ""]
    if x.get("api"):
        req, res = api_fields(x, "request"), api_fields(x, "response")
        L += [f"- **Open API** (GET, {x['api']['fmt']}), 일일 호출 한도 {x['api']['quota']}회",
              f"- 호출: `https://open.jejudatahub.net/api/proxy/{x['key']}/{{프로젝트키}}?파라미터`",
              "- 사전 조건: 로그인 → 프로젝트에 이 데이터 담기 → 프로젝트키 (guides/how-to-collect.md)", ""]
        if req:
            L += ["**요청 변수**", "", md_table(["이름", "설명", "타입", "필수", "예시"], [[e[1], e[2], e[3], e[4], e[5]] for e in req]), ""]
        if res:
            L += ["**응답 필드**", "", md_table(["이름", "설명", "예시"], [[e[1], e[2], e[5]] for e in res]), ""]
        if (x.get("start") or "") == (x.get("end") or ""):
            L += ["> 메타데이터 기간이 시작일만 적혀 있음 → 실제 제공 기간은 탐색 호출로 확인 필요", ""]
    if x.get("files"):
        L += ["- **파일**: 로그인 → 프로젝트 담기 → 상세 페이지 첨부파일에서 다운로드", "",
              md_table(["파일명", "용량(MB)", "다운로드수", "등록일시"],
                       [[f[0], round((f[1] or 0) / 1e6, 2), f[2], f[3]] for f in x["files"]]), ""]
    if x.get("link"):
        L += [f"- **링크(외부 원본)**: {x['link']}", ""]

    # 컬럼 / 샘플
    p = x.get("preview")
    if isinstance(p, list) and p and isinstance(p[0], list):
        hdr = [str(c).replace("\ufeff", "").strip() for c in p[0]]
        kcols = max((i for i, h in enumerate(hdr) if h), default=-1) + 1
        hdr = hdr[:kcols]
        L += ["## 컬럼", "", ", ".join(h for h in hdr if h) or "-", ""]
        body = [[str(c)[:40] for c in r[:kcols]] + [""] * (kcols - len(r[:kcols])) for r in p[1:6]]
        L += ["## 샘플 (미리보기 최대 5행)", "", md_table(hdr, body), ""]
    elif x.get("api"):
        L += ["## 컬럼", "", ", ".join(e[1] for e in api_fields(x, "response")) or "-", "", "## 샘플", "", "미리보기 없음", ""]
    else:
        L += ["## 컬럼", "", "미리보기 없음", "", "## 샘플", "", "미리보기 없음", ""]
    if rec["series"]:
        L += [f"> 반복 시리즈 '{rec['series']}'의 하나 (catalog/series.md)", ""]

    L += ["## 분석 결과", "", k["analysis"], "", "## 메모", "", k["notes"], ""]
    path = DATA / rec["card"]
    path.write_text("\n".join(L), encoding="utf-8")
    written.add(path.name)

for p in CARD_DIR.glob("*.md"):
    if p.name not in written:
        p.unlink()

# ----------------------------------------------------------------- catalog.jsonl

with open(CAT_DIR / "catalog.jsonl", "w", encoding="utf-8") as f:
    for rec, _ in recs:
        status = keep_from((DATA / rec["card"]).read_text(encoding="utf-8"), rec["id"])["status"]
        f.write(json.dumps(dict(rec, status=status), ensure_ascii=False) + "\n")

# ----------------------------------------------------------------- indexes

def line_rows(items):
    return [[r["id"], f"[{r['title']}](../{r['card']})", r["type"], r["period_meta"], r["spatial"], r["temporal"]] for r in items]


def line_rows_top(items):
    return [[r["id"], f"[{r['title']}]({r['card']})", r["type"], r["period_meta"], r["spatial"], r["temporal"]] for r in items]


ALL = [r for r, _ in recs]
cats = sorted({r["category"] for r in ALL}, key=lambda c: -sum(r["category"] == c for r in ALL))
os.makedirs(CAT_DIR / "by-category", exist_ok=True)
for old in (CAT_DIR / "by-category").glob("*.md"):
    old.unlink()
cat_files = {}
for c in cats:
    items = sorted([r for r in ALL if r["category"] == c], key=lambda r: (r["series"] != "", -r["views"]))
    fn = slug(c.replace(", ", "-"), 20) + ".md"
    cat_files[c] = fn
    non_series = [r for r in items if not r["series"]]
    ser = collections.Counter(r["series"] for r in items if r["series"])
    body = [f"# {c} ({len(items)}건)", "",
            "조회수 순. 반복 시리즈는 아래에 묶어 표시. 열: ID · 데이터명 · 형태 · 수집기간(메타) · 공간(추정) · 시간(추정)", "",
            md_table(["ID", "데이터명", "형태", "기간(메타)", "공간", "시간"],
                     [[r["id"], f"[{r['title']}](../../{r['card']})", r["type"], r["period_meta"], r["spatial"], r["temporal"]] for r in non_series]), ""]
    if ser:
        body += ["## 반복 시리즈", ""] + [f"- {k}: {v}건 → [series.md](../series.md)" for k, v in ser.items()] + [""]
    (CAT_DIR / "by-category" / fn).write_text("\n".join(body), encoding="utf-8")

# INDEX.md
tc = collections.Counter
ey = tc(r["end_year"] for r in ALL)
yrs = sorted(k for k in ey if k.isdigit())
idx = ["# 제주데이터허브 카탈로그 색인", "",
       f"- 총 {len(ALL)}건 · 수집일 {COLLECTED_AT} · 출처 jejudatahub.net 공개 카탈로그",
       f"- 제공형태: API {sum('API' in r['type'] for r in ALL)} · 파일 {sum('파일' in r['type'] for r in ALL)} · 링크 {sum('링크' in r['type'] for r in ALL)} (중복 포함)",
       f"- 첨부파일 총 {round(sum(r['file_size_mb'] for r in ALL) / 1000, 1)} GB",
       "", "## 어떤 색인을 볼까", "",
       md_table(["질문", "파일"], [
           ["분야별로 무엇이 있나", "by-category/ (아래 표)"],
           ["특정 주제(버스, 유동인구, 관광 수요 …)의 데이터", "[by-theme/](by-theme/README.md)"],
           ["API·최신·좌표·대용량 등 조건별 목록", "[by-attribute/](by-attribute/README.md)"],
           ["이 데이터와 엮을 수 있는 데이터", "[join-keys/](join-keys/README.md)"],
           ["같은 형식 반복 데이터 묶음", "[series.md](series.md)"],
           ["조건 조합 검색 (기계용)", "catalog.jsonl (jq)"],
       ]), "",
       "## 분야별", "",
       md_table(["분야", "건수", "API", "파일", "링크", "색인"],
                [[c, sum(r["category"] == c for r in ALL),
                  sum(r["category"] == c and "API" in r["type"] for r in ALL),
                  sum(r["category"] == c and "파일" in r["type"] for r in ALL),
                  sum(r["category"] == c and "링크" in r["type"] for r in ALL),
                  f"[{cat_files[c]}](by-category/{cat_files[c]})"] for c in cats]), "",
       "## 최신성 (수집 종료연도, 메타 기준)", "",
       md_table(["종료연도", "건수"], [[y, ey[y]] for y in yrs] + [["계속(미정)", ey["계속(미정)"]], ["미기재", ey["미기재"]]]), "",
       "## 단위 분포 (추정)", "",
       md_table(["공간단위", "건수"], tc(r["spatial"] or "없음/불명" for r in ALL).most_common()), "",
       md_table(["시간단위", "건수"], tc(r["temporal"] for r in ALL).most_common()), ""]
(CAT_DIR / "INDEX.md").write_text("\n".join(idx), encoding="utf-8")


def write_folder(folder, title, intro, groups, extra_col=None):
    """groups: list of (name, items). 하나의 그룹 = 하나의 파일 + 폴더 README."""
    d = CAT_DIR / folder
    d.mkdir(exist_ok=True)
    for old in d.glob("*.md"):
        old.unlink()
    readme = [f"# {title}", "", intro, "", md_table(["묶음", "건수", "파일"],
              [[n, len(it), f"[{slug(n, 30)}.md]({slug(n, 30)}.md)"] for n, it in groups]), ""]
    (d / "README.md").write_text("\n".join(readme), encoding="utf-8")
    for n, items in groups:
        hdr = ["ID", "데이터명", "형태", "기간(메타)", "공간", "시간"] + ([extra_col[0]] if extra_col else [])
        rows = [[r["id"], f"[{r['title']}](../../{r['card']})", r["type"], r["period_meta"], r["spatial"], r["temporal"]]
                + ([extra_col[1](r)] if extra_col else []) for r in items]
        (d / f"{slug(n, 30)}.md").write_text("\n".join([f"# {n} ({len(items)}건)", "", intro, "", md_table(hdr, rows), ""]), encoding="utf-8")


order_t = {"API": 0, "API+파일": 0, "파일": 1, "파일+링크": 1, "링크": 2, "없음": 3}
tsort = lambda r: (order_t.get(r["type"], 3), -r["views"])

# by-theme/
write_folder("by-theme", "주제군별 데이터",
             "제목·태그·설명 키워드로 분류(한 데이터가 여러 주제군에 들어갈 수 있음). 반복 시리즈는 제외(series.md). 정렬: API → 파일 → 링크, 같은 형태는 조회수 순.",
             [(name, sorted([r for r in ALL if name in r["themes"] and not r["series"]], key=tsort)) for name, _ in THEMES])

# by-attribute/
def recent(r):
    return r["end_year"] == "계속(미정)" or (r["end_year"].isdigit() and int(r["end_year"]) >= 2023)


attr_groups = [
    ("Open API 전체", sorted([r for r in ALL if "API" in r["type"]], key=lambda r: (r["category"], -r["views"]))),
    ("최근 데이터 (종료 2023년 이후·계속, 링크 제외)", sorted([r for r in ALL if recent(r) and r["type"] != "링크" and not r["series"]], key=lambda r: (r["end_year"] != "계속(미정)", -int(r["end_year"]) if r["end_year"].isdigit() else 0))),
    ("일·시간 단위 시계열 (링크 제외)", sorted([r for r in ALL if r["temporal"] in ("일", "시간") and r["type"] != "링크" and not r["series"]], key=lambda r: -r["views"])),
    ("좌표 단위", sorted([r for r in ALL if r["spatial"] == "좌표" and not r["series"]], key=lambda r: -r["views"])),
    ("읍면동·격자 단위", sorted([r for r in ALL if r["spatial"] in ("읍면동", "격자") and not r["series"]], key=lambda r: -r["views"])),
    ("대용량 파일 (50MB 이상)", sorted([r for r in ALL if r["file_size_mb"] >= 50], key=lambda r: -r["file_size_mb"])),
    ("조회수 상위 50", sorted(ALL, key=lambda r: -r["views"])[:50]),
]
write_folder("by-attribute", "조건별 데이터 목록", "조건은 메타데이터·컬럼명 기준 추정. 실제 기간은 원본 확인 필요.",
             attr_groups, extra_col=("파일MB", lambda r: r["file_size_mb"] or ""))

# join-keys/
write_folder("join-keys", "연결 키별 데이터",
             "컬럼명으로 추정한 공통 키. 같은 키를 가진 데이터끼리 결합을 검토할 수 있다. 키 값의 표기(코드/한글명, 형식)는 카드 샘플로 확인. 반복 시리즈 제외.",
             [(name, sorted([r for r in ALL if name in r["join_keys"] and not r["series"]], key=tsort)) for name, _ in JOIN_RULES],
             extra_col=("다른 키", lambda r: ", ".join(r["join_keys"])))

# series.md
se = ["# 반복 시리즈", "", "같은 형식으로 장소·주제만 바꿔 여러 건 등록된 데이터. 색인에서는 접어서 보여준다.", ""]
for name, _, desc in SERIES_RULES:
    items = sorted([r for r in ALL if r["series"] == name], key=lambda r: r["title"])
    if not items:
        continue
    se += [f"## {name} ({len(items)}건)", "", desc, "",
           md_table(["ID", "데이터명", "형태", "기간(메타)"], [[r["id"], f"[{r['title']}](../{r['card']})", r["type"], r["period_meta"]] for r in items]), ""]
(CAT_DIR / "series.md").write_text("\n".join(se), encoding="utf-8")

print(f"cards={len(written)} categories={len(cats)} themes={len(THEMES)} series={sum(1 for r in ALL if r['series'])}")
