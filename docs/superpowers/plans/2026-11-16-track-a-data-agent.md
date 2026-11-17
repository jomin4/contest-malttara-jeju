# 말따라 제주 A 트랙(데이터·에이전트) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 허브 데이터로 SQLite를 만들고, 그 위에서 경로 생성·검증·수정·재설계를 하는 에이전트와 표준 라이브러리 HTTP 서버를 만든다.

**Architecture:** 개발 PC에서만 도는 ETL(`src/malttara/etl/`)이 `data/raw/`의 원본과 외부 API 스냅샷을 `data/db/malttara.sqlite`와 `data/db/map.json`으로 만든다. 실행 중에는 결정론적 Tool(`tools/`)과 LLM-또는-규칙 판단(`agent/`)을 코드 고정 파이프라인(Batch A/B)이 호출하고, 표준 라이브러리 서버(`server/`)가 계약 API와 빌드된 프론트를 서빙한다.

**Tech Stack:** Python 3.11 문법(개발 PC 3.14에서도 동작), 표준 라이브러리만(실행 중), `unittest`. ETL만 `pyshp`·`pyproj`(경계 변환) 허용.

**Spec:** `docs/superpowers/specs/2026-11-16-malttara-jeju-design.md` · **계약:** `docs/superpowers/plans/2026-11-16-api-contract.md`

## Global Constraints

- 실행 중 코드(`src/malttara/` 중 `etl/` 제외, `run.py`)는 **표준 라이브러리만** import한다. `requirements.txt`는 비어 있다. ETL 의존성은 `requirements-etl.txt`.
- Python 3.11 문법 범위(3.12 전용 문법 금지: `type` 문, PEP 695 제네릭, 중첩 따옴표 f-string).
- 설정은 `config/*.json`(YAML 금지: 실행 중 표준 라이브러리로 읽어야 함). 가중치·반경·임계값을 코드에 박지 않는다.
- 수치는 Tool 결과에서만 나온다. LLM 출력에서 숫자를 받아 쓰지 않는다(LLM은 선택지 고르기와 문장 다듬기만).
- 사용자가 입력하지 않은 조건은 `null`(미반영). 기본값으로 채워 넣지 않는다(pace 미반영은 계산에만 "보통" 규칙을 쓰고 Goal에는 `null` 유지).
- 읍면동 지표(563)와 장소 반경 지표(1208)는 항상 다른 키(`indicators.region` / `indicators.nearby`)로 낸다.
- 거리는 하버사인 직선거리. 이동 시간을 계산·출력하지 않는다.
- `.env`의 키(`HUB_PROJECT_KEY`, `DATA_GO_KR_KEY`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`)는 코드에 하드코딩하지 않는다. `data/raw/`, `data/db/`, `.env`, `submission/`은 커밋하지 않는다(`.gitignore` 이미 있음).
- 테스트 실행(Git Bash, 프로젝트 루트): `PYTHONPATH=src python -m unittest discover -s tests -v`. 각 테스트 파일은 `tests/` 바로 아래. `run.bat`·매뉴얼은 cmd 문법(`set PYTHONPATH=src`).
- 가상 탐험(`virtual_arrival`)과 실제 방문(`visited`)은 `user_interactions.type`으로 구분 저장.

## Review Focus

1. **LLM 키가 없거나 인터넷이 끊김** → 모든 판단 지점이 규칙으로 넘어가고 전 흐름이 끝까지 돈다(Task 11, 15에서 고정).
2. **입력에 기간이 없음/이상한 기간("0박", "10박 11일")** → `missing: ["days"]` 또는 범위 오류로 막고, 배치를 시작하지 않는다(Task 10, 14).
3. **후보가 부족한 권역·관심사(예: 카페만 요청, 장소 적은 권역)** → 인접 권역 확장 후에도 부족하면 `count` 위반으로 남기고 화면에 보인다. 예외로 죽지 않는다(Task 8, 12).
4. **지표가 없는 장소(읍면동 매칭 실패, 1208 범위 밖)** → 0.5 중립 점수 + `missing: true`, 품질 집계에 반영(Task 7).
5. **LLM이 허용 목록 밖 행동·없는 place_id·숫자를 지어냄** → 검증 실패로 규칙 폴백, 숫자는 템플릿 값만 남는다(Task 11, 12).

---

## 파일 구조

```
config/settings.json      가중치, k, 거리 상한, 반경, 재시도 수, 서버 포트
config/regions.json       권역 → 읍면동 목록, 동(洞) 지역 규칙, 산간 박스(선택)
config/interests.json     관심사 → 분류·키워드, 입력 트리거 단어, 한적함 트리거
config/etl.json           본섬 범위, 부속섬 규칙, 비장소 키워드, 매칭 임계값, 키워드 분류
data/mapping/emd_alias.csv        법정동/표기 → 563 읍면동 키 (수작업)
data/mapping/sights_to_places.csv 189/190 관광지명 → place_id (수작업)
src/malttara/__init__.py
src/malttara/config.py    load_config(), load_env()
src/malttara/geo.py       haversine_km(), pct_rank(), centroid()
src/malttara/db.py        SCHEMA, connect(), 조회 함수
src/malttara/etl/         names.py clean_places.py categorize.py emd_stats.py quiet.py sights.py
                          fetch_tourapi.py fetch_hub.py boundaries.py build_db.py mock_data.py
src/malttara/tools/       places.py route.py itinerary.py validate.py revise.py goal.py
                          feedback.py compare.py quests.py explain.py
src/malttara/agent/       schema_lite.py llm.py decide.py planner.py state.py batch_a.py batch_b.py
src/malttara/server/      app.py routes.py
run.py, run.bat, requirements.txt(빈 파일), requirements-etl.txt
tests/                    test_*.py, tests/fixtures/
```

---

### Task 1: 골격 · 설정 · 기하 유틸

**Files:**
- Create: `config/settings.json`, `config/regions.json`, `config/interests.json`, `config/etl.json`, `src/malttara/__init__.py`, `src/malttara/config.py`, `src/malttara/geo.py`, `requirements.txt`(빈), `requirements-etl.txt`
- Test: `tests/test_config_geo.py`

**Interfaces:**
- Produces: `load_config(name: str) -> dict` (`config/{name}.json`), `load_env(path: str = ".env") -> dict[str, str]` (없으면 `{}`; `os.environ` 값이 우선), `haversine_km(lat1, lon1, lat2, lon2) -> float`, `pct_rank(x: float, values: list[float]) -> float`, `centroid(points: list[tuple[float, float]]) -> tuple[float, float]`

설정 초기값(설계 6.2~6.5 값 그대로):
```json
// settings.json
{"weights": {"default": [0.6, 0.2, 0.2], "quiet": [0.4, 0.3, 0.3]},
 "missing_indicator_value": 0.5, "feedback_interest_boost": 0.2, "quiet_radius_km": 1.0,
 "pace_k": {"여유롭게": 3, "보통": 4, "빡빡하게": 5}, "default_pace": "보통",
 "max_daily_km": 60, "max_regions_per_day": {"default": 1, "빡빡하게": 2},
 "max_origin_km": 30, "max_revisions": 2, "alternatives_per_place": 2,
 "llm": {"timeout_s": 20}, "server": {"host": "127.0.0.1", "port": 8765}}
```
- `regions.json`: `{"regions": [{"region_id": "city", "name": "제주시내권", "dong_of": "제주시"}, {"region_id": "west", "name": "서부권", "emds": ["제주시 애월읍", "제주시 한림읍", "제주시 한경면", "서귀포시 대정읍", "서귀포시 안덕면"]}, {"region_id": "east", "name": "동부권", "emds": ["제주시 조천읍", "제주시 구좌읍", "서귀포시 성산읍", "서귀포시 표선면"]}, {"region_id": "south", "name": "중문·서귀포권", "dong_of": "서귀포시", "emds": ["서귀포시 남원읍"]}], "adjacent": {"city": ["west", "east"], "west": ["city", "south"], "east": ["city", "south"], "south": ["west", "east"]}}` — **4권역 확정**(912 원본 `TRRSRT_AREA_NM` 값: 제주시내권·서부권·동부권·중문/서귀포). 중산간 권역 없음.
- `interests.json`: `{"interests": {"바다": {"categories": ["해수욕장", "해변", "포구", "해안"], "triggers": ["바다", "해변", "해수욕", "오션"]}, "오름": {...["오름"]}, "숲": {"categories": ["숲", "휴양림", "공원"], "triggers": ["숲", "산책", "휴양림"]}, "실내·전시": {"categories": ["박물관", "미술관", "전시"], "triggers": ["박물관", "미술관", "전시", "실내"]}, "체험·레저": {"categories": ["레포츠", "체험"], "triggers": ["체험", "레저", "액티비티"]}, "음식": {"categories": ["음식점"], "triggers": ["음식", "맛집", "식당", "먹고", "미식"], "slot": true}, "카페": {"categories": ["카페"], "triggers": ["카페", "커피"], "slot": true}}, "quiet_triggers": ["조용", "한적", "덜 붐비", "사람 적"]}` — `slot: true`는 하루 1곳 슬롯(설계 6.3-4). 실제 분류 값은 Task 6에서 TourAPI 원본을 보고 채운다.
- `etl.json`: `{"bbox": {"min_lat": 33.10, "max_lat": 33.60, "min_lon": 126.10, "max_lon": 127.00}, "island_address_tokens": ["우도면", "추자면", "마라리", "가파리"], "island_circles": [{"name": "비양도", "lat": 33.4069, "lon": 126.2270, "r_km": 0.8}], "non_place_keywords": ["렌트카", "렌터카", "반납", "공항", "여객터미널", "터미널", "주차장"], "name_prefixes": ["제주"], "match": {"exact_max_m": 300, "fuzzy_max_m": 100, "fuzzy_min_sim": 0.6}, "keyword_categories": {"해수욕장": "해수욕장", "해변": "해수욕장", "포구": "포구", "오름": "오름", "숲길": "숲", "휴양림": "휴양림", "박물관": "박물관", "미술관": "미술관", "폭포": "폭포", "카페": "카페"}}` (비양도 좌표·반경은 원본으로 확인)

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/test_config_geo.py`
```python
class ConfigGeoTest(unittest.TestCase):
    def test_settings_values_from_spec(self):
        s = load_config("settings")
        self.assertEqual(s["weights"]["default"], [0.6, 0.2, 0.2])
        self.assertEqual(s["pace_k"], {"여유롭게": 3, "보통": 4, "빡빡하게": 5})
        self.assertEqual(s["max_daily_km"], 60)
    def test_haversine_known_distance(self):
        # 제주시청(33.4996,126.5312) ↔ 서귀포시청(33.2541,126.5600) ≈ 27.4km
        self.assertAlmostEqual(haversine_km(33.4996, 126.5312, 33.2541, 126.5600), 27.4, delta=0.5)
    def test_pct_rank(self):
        vals = [1.0, 2.0, 3.0, 4.0, 5.0]
        self.assertEqual(pct_rank(1.0, vals), 0.0)
        self.assertEqual(pct_rank(5.0, vals), 1.0)
        self.assertEqual(pct_rank(3.0, vals), 0.5)
        self.assertEqual(pct_rank(2.0, [2.0]), 0.5)   # 값 1개면 중립
    def test_load_env_missing_file(self):
        self.assertEqual(load_env("nope.env"), {})
```
- [ ] **Step 2: 실패 확인** — Run: `PYTHONPATH=src python -m unittest tests.test_config_geo -v` → Expected: FAIL (ImportError)
- [ ] **Step 3: 구현** — 위 Interfaces 시그니처. `pct_rank = (#values < x) / (len(values) - 1)`, `len(values) <= 1`이면 0.5. `load_env`는 `KEY=VALUE` 줄만 파싱(`#` 주석·따옴표 제거).
- [ ] **Step 4: 통과 확인** — 같은 명령 → PASS
- [ ] **Step 5: Commit** — `git add config src tests requirements*.txt && git commit -m "feat(a): 프로젝트 골격, 설정, 기하 유틸"`

---

### Task 2: DB 스키마 · 조회 함수 · 모의 데이터

모의 DB로 Task 7 이후 TDD를 원본 없이 시작한다(설계 10.1).

**Files:**
- Create: `src/malttara/db.py`, `src/malttara/etl/__init__.py`(빈 파일 — 무거운 패키지 import 금지), `src/malttara/etl/mock_data.py`(표준 라이브러리만)
- Test: `tests/test_db.py`

**Interfaces:**
- Produces:
  - `SCHEMA: str` — 테이블: `regions(region_id PK, name)`, `emd_stats(emd, month INT, visit_pop, resident_pop, visit_ratio, period, source_id, PK(emd, month))` (month 0 = 연평균), `places(place_id PK, name, lat, lon, emd, region_id, category, category_source, overview, source, quiet_count, in_scope INT)`, `sight_visits(place_id, year_month, domestic, foreign, source_id)`, `data_sources(source_id PK, name, url, fetched_at, period_actual, rows, license, notes)`, `batches(batch_id PK, kind, prev_batch_id, goal_json, result_json, created_at)`, `agent_decisions(id PK, batch_id, point, actor, options_json, choice_json, reason, created_at)`, `user_interactions(id PK, batch_id, place_id, type, value, created_at)`, `meta(key PK, value)`.
  - `connect(path: str) -> sqlite3.Connection` (row_factory=Row, 스키마 보장)
  - `all_places(conn) -> list[dict]` (`in_scope=1`만), `emd_stats(conn, month: int | None) -> dict[str, dict]` (month None → 0), `place_trend(conn, place_id) -> list[dict]`, `region_names(conn) -> dict[str, str]`, `meta_get(conn, key) -> str | None`
  - `build_mock_db(path: str) -> None` — 4권역 × 권역당 8곳(분류: 해수욕장·오름·숲·박물관·음식점·카페 섞음), 각 장소 `emd`·`quiet_count` 일부 `NULL`, `emd_stats` 월 0·11, `sight_visits` 2곳, `meta.data_version="mock"`. place_id는 `p-mock-{region}-{i:02d}`. 결정론적(난수 없음).

- [ ] **Step 1: 실패하는 테스트 작성**
```python
class DbTest(unittest.TestCase):
    def setUp(self):
        self.path = os.path.join(tempfile.mkdtemp(), "t.sqlite"); build_mock_db(self.path)
        self.conn = connect(self.path)
    def test_mock_has_all_regions_and_categories(self):
        places = all_places(self.conn)
        self.assertEqual({p["region_id"] for p in places}, {"city", "west", "east", "south"})
        self.assertTrue({"해수욕장", "음식점", "카페"} <= {p["category"] for p in places})
    def test_mock_has_missing_indicators(self):
        places = all_places(self.conn)
        self.assertTrue(any(p["quiet_count"] is None for p in places))
        self.assertTrue(any(p["emd"] not in emd_stats(self.conn, None) for p in places))
    def test_emd_stats_month_fallback(self):
        self.assertTrue(emd_stats(self.conn, None)); self.assertTrue(emd_stats(self.conn, 11))
```
- [ ] **Step 2: 실패 확인** — `PYTHONPATH=src python -m unittest tests.test_db -v` → FAIL
- [ ] **Step 3: 구현** — 위 시그니처.
- [ ] **Step 4: 통과 확인** → PASS
- [ ] **Step 5: Commit** — `git commit -m "feat(a): SQLite 스키마, 조회 함수, 모의 DB"`

---

### Task 3: ETL — 이름 정규화 · 1349 정제 · 읍면동·권역 판정

**Files:**
- Create: `src/malttara/etl/names.py`, `src/malttara/etl/clean_places.py`, `data/mapping/emd_alias.csv`(헤더만: `raw,emd`)
- Test: `tests/test_etl_clean.py`

**Interfaces:**
- Produces:
  - `normalize_name(name: str, prefixes: list[str]) -> str` — 괄호와 그 안, 공백, 특수문자 제거, 접두어(`제주`) 제거, 소문자.
  - `name_similarity(a: str, b: str) -> float` — `difflib.SequenceMatcher` 비율(정규화 후).
  - **읍면동은 좌표로 정한다**(1349 지번주소에 틀린 값이 있음: 예 "김녕해수욕장"·"메이즈랜드"가 모두 "제주시 오라동 34-14"). `emd_of_point(lat, lon, polygons: list[tuple[str, list[list[tuple[float, float]]]]]) -> str | None` — 행정동 경계(`vuski/admdongkor` `ver20261001`, `adm_nm`에서 "제주특별자치도 " 제거 → `"제주시 애월읍"`)에 대한 ray-casting 점-다각형 판정. 경계 밖이면 None.
  - `parse_emd(jibun_address: str, alias: dict[str, str]) -> str | None` — 경계가 없을 때만 쓰는 폴백: "제주특별자치도 제주시 한림읍 협재리 2447" → `"제주시 한림읍"`, "… 제주시 용담2동 …" → `"제주시 용담2동"`, alias 우선.
  - `assign_region(emd: str | None, regions_cfg: dict) -> str | None` — `emds` 목록, 그다음 `dong_of`(해당 시의 `…동`).
  - `is_island(address: str, lat: float, lon: float, cfg: dict) -> bool`, `is_non_place(name: str, cfg: dict) -> bool`
  - `clean_1349(rows: list[dict], cfg: dict, regions_cfg: dict, alias: dict, polygons=None) -> list[dict]` — emd는 `polygons`가 있으면 `emd_of_point`, 없으면 `parse_emd`. 입력 행 키: `장소명, 지번주소, 위도, 경도`. bbox 밖·부속섬·비장소 제외, 같은 정규화 이름 + 50m 이내 중복 제거. 출력 dict: `place_id("p1349-{원본행번호:05d}"), name, lat, lon, emd, region_id, source="1349", in_scope=1`.

- [ ] **Step 1: 실패하는 테스트 작성**
```python
def test_clean_1349_drops_outside_island_nonplace(self):
    rows = [
        {"장소명": "협재해수욕장", "지번주소": "제주특별자치도 제주시 한림읍 협재리 2447", "위도": "33.3934", "경도": "126.2396"},
        {"장소명": "대구공항", "지번주소": "대구광역시 동구 지저동 400-5", "위도": "35.8998", "경도": "128.6373"},
        {"장소명": "렌트카반납", "지번주소": "제주특별자치도 제주시 용담2동 1032-4", "위도": "33.5159", "경도": "126.5032"},
        {"장소명": "우도봉", "지번주소": "제주특별자치도 제주시 우도면 연평리 산1", "위도": "33.4990", "경도": "126.9680"},
    ]
    out = clean_1349(rows, load_config("etl"), load_config("regions"), {}, polygons=None)   # 경계 없으면 주소 폴백
    self.assertEqual([p["name"] for p in out], ["협재해수욕장"])
    self.assertEqual(out[0]["emd"], "제주시 한림읍"); self.assertEqual(out[0]["region_id"], "west")
def test_normalize_name(self):
    self.assertEqual(normalize_name("제주 민속자연사박물관 (본관)", ["제주"]), "민속자연사박물관")
def test_parse_emd_dong(self):
    self.assertEqual(parse_emd("제주특별자치도 서귀포시 서홍동 1", {}), "서귀포시 서홍동")
    self.assertEqual(assign_region("서귀포시 서홍동", load_config("regions")), "south")
def test_emd_of_point_square(self):
    sq = [("제주시 테스트동", [[(33.0, 126.0), (33.0, 126.1), (33.1, 126.1), (33.1, 126.0)]])]
    self.assertEqual(emd_of_point(33.05, 126.05, sq), "제주시 테스트동"); self.assertIsNone(emd_of_point(33.2, 126.05, sq))
```
- [ ] **Step 2: 실패 확인** — `PYTHONPATH=src python -m unittest tests.test_etl_clean -v` → FAIL
- [ ] **Step 3: 구현** — 표준 라이브러리만(`re`, `difflib`).
- [ ] **Step 4: 통과 확인** → PASS
- [ ] **Step 5: Commit** — `git commit -m "feat(a): ETL 이름 정규화, 1349 정제, 권역 판정"`

---

### Task 4: ETL — 분류 매칭 · 외부/허브 API 스냅샷

**Files:**
- Create: `src/malttara/etl/categorize.py`, `src/malttara/etl/fetch_tourapi.py`, `src/malttara/etl/fetch_hub.py`
- Test: `tests/test_etl_categorize.py`

**Interfaces:**
- Consumes: `normalize_name`, `name_similarity`, `haversine_km`
- Produces:
  - `match_reference(place: dict, refs: list[dict], match_cfg: dict, prefixes: list[str]) -> dict | None` — refs 항목 키: `name, lat, lon, category, overview?`. 규칙(설계 5.4-2): 정규화 이름 같고 ≤ `exact_max_m` → 매칭, 아니면 ≤ `fuzzy_max_m` 안 최근접 중 유사도 ≥ `fuzzy_min_sim` → 매칭. ref에 좌표가 없으면(784 해수욕장 정보) 정규화 이름 완전 일치만 본다.
  - `categorize_places(places: list[dict], ref_sets: list[tuple[str, list[dict]]], cfg: dict) -> dict[str, int]` — `ref_sets` 순서 `[("tourapi", …), ("hub_811", …), ("hub_812", …), ("hub_784", …), ("hub_858", …)]`. 앞에서 매칭되면 `category`, `category_source`, `overview`(tourapi만) 기록, 남으면 `keyword_categories` 부분 문자열 규칙 → `"keyword"`, 없으면 `category=None, category_source="none"`. 반환: source별 건수(매칭률 기록용). places를 제자리 수정.
  - `fetch_tourapi(api_key: str, out_path: str) -> int` — 제주 지역 코드, 유형(관광지·문화시설·레포츠·쇼핑·음식점) 목록 + 개요를 받아 `[{content_id, name, lat, lon, content_type, cat1, cat2, cat3, category, overview}]` JSON으로 저장, 건수 반환. `category`는 소분류 이름(cat3 코드표로 변환). 엔드포인트 버전·파라미터는 공식 문서로 확인하고 파일 상단 주석에 문서 URL과 확인일을 적는다. `urllib.request`, 페이지당 100건, 호출 사이 0.2초.
  - `fetch_hub_api(project_key: str, dataset: str, out_path: str) -> int` — `dataset in {"811", "812"}`, 카드(`data/cards/0811_*.md`, `0812_*.md`)의 호출 주소 형식 사용. 출력 `[{name, lat, lon, category}]`(category = 카테고리 문자열의 마지막 단계).

- [ ] **Step 1: 실패하는 테스트 작성**
```python
def test_exact_name_within_300m_matches(self):
    p = {"name": "협재해수욕장", "lat": 33.3934, "lon": 126.2396}
    refs = [{"name": "협재 해수욕장", "lat": 33.3940, "lon": 126.2400, "category": "해수욕장"}]
    self.assertEqual(match_reference(p, refs, CFG["match"], ["제주"])["category"], "해수욕장")
def test_far_same_name_does_not_match(self):
    p = {"name": "협재해수욕장", "lat": 33.3934, "lon": 126.2396}
    refs = [{"name": "협재해수욕장", "lat": 33.4100, "lon": 126.2600, "category": "해수욕장"}]  # ~2.6km
    self.assertIsNone(match_reference(p, refs, CFG["match"], ["제주"]))
def test_categorize_order_and_keyword_fallback(self):
    places = [{"place_id": "a", "name": "새별오름", "lat": 33.36, "lon": 126.35},
              {"place_id": "b", "name": "이름없는곳", "lat": 33.40, "lon": 126.40}]
    counts = categorize_places(places, [("tourapi", []), ("hub_811", [])], CFG)
    self.assertEqual(places[0]["category_source"], "keyword"); self.assertEqual(places[0]["category"], "오름")
    self.assertEqual(places[1]["category_source"], "none")
    self.assertEqual(counts["keyword"], 1)
```
- [ ] **Step 2: 실패 확인** — `PYTHONPATH=src python -m unittest tests.test_etl_categorize -v` → FAIL
- [ ] **Step 3: 구현** — fetch 함수는 테스트하지 않는다(네트워크). 매칭 함수만 TDD.
- [ ] **Step 4: 통과 확인** → PASS
- [ ] **Step 5: 스냅샷 받기(키가 있을 때)** — Run: `PYTHONPATH=src python -m malttara.etl.fetch_tourapi` / `python -m malttara.etl.fetch_hub 811` / `… 812` → Expected: `data/raw/tourapi_jeju.json`, `data/raw/hub_811.json`, `data/raw/hub_812.json` 생성, 건수 출력. 키가 아직 없으면 이 단계는 Task 6으로 미룬다.
- [ ] **Step 6: Commit** — `git commit -m "feat(a): 분류 매칭, TourAPI·허브 API 스냅샷"`

---

### Task 5: ETL — 563 읍면동 집계 · 1208 반경 집계 · 189/190 매칭

**Files:**
- Create: `src/malttara/etl/emd_stats.py`, `src/malttara/etl/quiet.py`, `src/malttara/etl/sights.py`, `data/mapping/sights_to_places.csv`(헤더: `sight_name,place_id`), `tests/fixtures/563_sample.csv`, `tests/fixtures/1208_sample.csv`
- Test: `tests/test_etl_stats.py`

**Interfaces:**
- Produces:
  - `aggregate_563(csv_path: str, alias: dict[str, str]) -> list[dict]` — `csv` 모듈로 한 줄씩 스트리밍(2.4GB). 키: `emd_name`(alias 적용), `base_year_month`의 월. 같은 (emd, 연월)의 `visit_population_count`·`residence_population_count`를 합한 뒤, (emd, 월)별로 연월 평균 → 월 1~12 행과 month 0(전체 연월 평균) 행. `visit_ratio = visit_pop / resident_pop`(resident 0이면 None). 출력 행에 `period`("YYYY-MM~YYYY-MM", 실제 최소~최대 연월), `source_id="563"`.
  - `quiet_counts(places: list[dict], points: Iterable[tuple[float, float]], radius_km: float) -> dict[str, int]` — 0.01° 격자 버킷으로 후보를 좁힌 뒤 하버사인 ≤ radius. 반경 안에 점이 없으면 0, 장소가 점 분포의 bbox(+radius) 밖이면 키를 넣지 않는다(→ 지표 없음).
  - `read_1208_points(paths: list[str]) -> Iterator[tuple[float, float]]` — `latitude, longitude` 컬럼.
  - `match_sights(sight_names: list[str], places: list[dict], manual: dict[str, str], prefixes: list[str]) -> dict[str, str]` — 수작업표 우선, 그다음 정규화 이름 완전 일치(접미 `관광지`도 제거해 비교). 반환 `{sight_name: place_id}`.
  - `aggregate_sights(csv_paths: dict[str, str], mapping: dict[str, str]) -> list[dict]` — `csv_paths = {"domestic": 189경로, "foreign": 190경로}`, 날짜 `2009.01`/`200901` 모두 `YYYY-MM`로. 출력 `{place_id, year_month, domestic, foreign, source_id: "189,190"}`.

- [ ] **Step 1: 실패하는 테스트 작성** — 픽스처: 563 샘플 6행(같은 emd 2개월 × 성별 2 + 다른 emd 2행), 1208 샘플 5점.
```python
def test_aggregate_563_month_and_annual(self):
    rows = aggregate_563(FIX + "/563_sample.csv", {})
    m0 = [r for r in rows if r["emd"] == "서귀포시 남원읍" and r["month"] == 0][0]
    self.assertAlmostEqual(m0["visit_ratio"], m0["visit_pop"] / m0["resident_pop"])
    self.assertEqual(m0["period"], "2018-01~2018-02")
    self.assertEqual({r["month"] for r in rows if r["emd"] == "서귀포시 남원읍"}, {0, 1, 2})
def test_quiet_counts_radius(self):
    places = [{"place_id": "a", "lat": 33.40, "lon": 126.40}, {"place_id": "far", "lat": 33.10, "lon": 126.10}]
    pts = [(33.401, 126.401), (33.405, 126.405), (33.50, 126.50)]
    c = quiet_counts(places, pts, 1.0)
    self.assertEqual(c["a"], 2); self.assertNotIn("far", c)
def test_match_sights_strips_suffix(self):
    places = [{"place_id": "p1", "name": "만장굴"}]
    self.assertEqual(match_sights(["만장굴관광지"], places, {}, ["제주"]), {"만장굴관광지": "p1"})
```
- [ ] **Step 2: 실패 확인** — `PYTHONPATH=src python -m unittest tests.test_etl_stats -v` → FAIL
- [ ] **Step 3: 구현**
- [ ] **Step 4: 통과 확인** → PASS
- [ ] **Step 5: Commit** — `git commit -m "feat(a): 563 읍면동 집계, 1208 반경 집계, 입장객 매칭"`

---

### Task 6: ETL — 경계 → map.json · DB 빌드 · 원본 확인 기록

원본(`data/raw/`)이 들어온 뒤 실행한다(기한 11/17 12:00). 그 전에는 Step 1~4만.

**Files:**
- Create: `src/malttara/etl/boundaries.py`, `src/malttara/etl/build_db.py`
- Modify: `config/interests.json`(실제 TourAPI 분류 값), `data/mapping/*.csv`, `data/cards/{1349,0563,1208,0189,0190,0784,0858,0912}_*.md`의 '분석 결과'와 `status`, `docs/01_planning/data-selection.md` 5장 표
- Test: `tests/test_build_db.py`

**Interfaces:**
- Consumes: Task 3~5 함수 전부, `SCHEMA`
- Produces:
  - `build_map(boundary_path: str, regions_cfg: dict, alias: dict, out_path: str, tolerance: float) -> dict` — 행정동 경계 `data/raw/boundary/`의 `vuski/admdongkor` `ver20261001` GeoJSON(WGS84, 제주 43개만 사용 — 좌표계는 파일로 재확인, EPSG:5179면 pyproj 변환) → Douglas–Peucker 단순화 → 등장방형 투영 `x = (lon - min_lon) * scale * cos(33.4°)`, `y = (max_lat - lat) * scale` → 계약 `GET /api/map` 모양 JSON. 권역 외곽선은 같은 권역 읍면동 path를 이어 붙인 것(겹친 선 허용). 부속섬 읍면동은 제외.
  - `build_db(raw_dir: str, out_db: str, out_map: str) -> dict` — 순서: 1349 정제 → 분류(ref 세트: `tourapi_jeju.json`, `hub_811.json`, `hub_812.json`, 784 CSV(`해변명`→name, category `해수욕장`, 좌표 없음), 858 CSV(`장소명, 위도, 경도`, category `무장애 여행지`는 분류로 쓰지 않고 이름·좌표 검증용 — 매칭되면 keyword 규칙으로 분류). 파일이 없으면 그 세트는 건너뛰고 로그) → TourAPI 음식점·카페를 `places`에 추가(`place_id="ptour-{content_id}"`, `source="tourapi"`, 같은 정제 규칙) → 563 → 1208 → 189/190 → `data_sources`(행 수, 실제 기간, 매칭률) → `meta.data_version`(빌드 날짜). 반환: 단계별 건수 dict(콘솔 출력용).
  - CLI: `python -m malttara.etl.build_db` → `data/db/malttara.sqlite`, `data/db/map.json`

- [ ] **Step 1: 실패하는 테스트 작성** — `tests/fixtures/raw_min/`에 1349 3행, 563 샘플, 1208 샘플, 189/190 각 2행, 작은 GeoJSON(사각형 읍면동 2개).
```python
def test_build_db_from_minimal_raw(self):
    out = tempfile.mkdtemp()
    stats = build_db(FIX + "/raw_min", out + "/m.sqlite", out + "/map.json")
    conn = connect(out + "/m.sqlite")
    self.assertGreaterEqual(len(all_places(conn)), 1)
    self.assertTrue(emd_stats(conn, None))
    self.assertIsNotNone(meta_get(conn, "data_version"))
    self.assertIn("places", stats)
    m = json.load(open(out + "/map.json", encoding="utf-8"))
    self.assertTrue(m["emds"] and m["view_box"].startswith("0 0 "))
```
- [ ] **Step 2: 실패 확인** — `PYTHONPATH=src python -m unittest tests.test_build_db -v` → FAIL
- [ ] **Step 3: 구현** — `pyshp`/`pyproj`는 `boundaries.py` 안에서만 import(실행 중 코드가 import하지 않게).
- [ ] **Step 4: 통과 확인** → PASS
- [ ] **Step 5: 원본으로 빌드** — Run: `pip install -r requirements-etl.txt` 후 `PYTHONPATH=src python -m malttara.etl.build_db` → Expected: 단계별 건수 출력, `data/db/malttara.sqlite`·`map.json` 생성. 563이 2.4GB라 수 분 걸린다.
- [ ] **Step 6: 원본 확인 기록** — 컬럼·실제 기간·행 수·매칭률을 각 카드 '분석 결과'에 쓰고 `status: loaded`로. `data-selection.md` 5장 표 채우기. 컬럼이 안 맞는 데이터는 차순위(563→583, 1208→568)로 바꾸고 `decisions.md` 변경 이력에 기록. `interests.json`의 `categories`를 TourAPI 실제 소분류 값으로 갱신. 912의 `TRRSRT_AREA_NM` 값 목록을 확인해 `regions.json`의 권역 `name`을 맞춘다(경계는 그대로). 읍면동 표기 불일치는 `emd_alias.csv`에, 189/190 미매칭 주요 관광지는 `sights_to_places.csv`에 추가 후 재빌드.
- [ ] **Step 7: 오류 주입 예시 확정** — 서부 권역 일정에 넣을 동부 장소 1곳을 DB에서 골라 `config/settings.json`의 `"inject_example": {"day_region": "west", "place_id": "…"}`에 적는다(없으면 Task 9 기본 규칙 사용).
- [ ] **Step 8: Commit** — `git add src config data/mapping data/cards docs/01_planning tests && git commit -m "feat(a): 경계 지도, DB 빌드, 원본 확인 기록"` (`data/raw`, `data/db` 제외 확인)

---

### Task 7: Tool — 장소 점수 · 탐색 · 지역 지표 · 품질 · 관광 추이

**Files:**
- Create: `src/malttara/tools/__init__.py`, `src/malttara/tools/places.py`
- Test: `tests/test_tools_places.py`

**Interfaces:**
- Consumes: `all_places`, `emd_stats`, `place_trend`, `pct_rank`, 설정
- Produces:
  - `score_places(conn, goal: dict, settings: dict, interests_cfg: dict, boosts: dict[str, float] | None = None) -> list[dict]` — 범위 내 전체 장소에 계약 Place 필드(`score, interest, spread, quiet, indicators, region_name, has_trend`)를 붙여 `(-score, place_id)` 순으로 정렬해 반환. 설계 6.2:
    - interest: `goal["interests"]`가 비면 1.0. 아니면 장소 `category`가 관심사(slot 관심사 제외) categories에 있으면 1.0, 아니면 0.0. slot 관심사(음식·카페) 분류 장소는 interest 1.0이지만 일반 후보에서 빠진다(Task 8). `boosts[category]`를 더하고 상한 1.2.
    - spread: `1 - pct_rank(visit_ratio, 범위 내 모든 읍면동 visit_ratio)`, month=`goal["month"]`(없으면 0). 없으면 `missing_indicator_value` + `missing: true`.
    - quiet: `1 - pct_rank(quiet_count, 범위 내 모든 quiet_count)`, 없으면 0.5 + `missing: true`.
    - 가중치: `goal["quiet_pref"]`면 `weights.quiet` 아니면 `weights.default`.
  - `search_places(conn, goal, settings, interests_cfg, region_ids: list[str] | None = None, exclude_ids: set[str] | None = None, limit: int = 50, boosts=None, slot: str | None = None) -> list[dict]` — `slot=None`이면 slot 분류 제외 일반 후보, `slot="음식"`이면 그 분류만.
  - `get_region_data(conn, month: int | None) -> dict` — 계약 `GET /api/stats/emd` 응답 모양.
  - `check_data_quality(places: list[dict]) -> dict` — `{"no_category", "no_region_indicator", "no_nearby_indicator"}` 건수.
  - `analyze_tourism(conn, place_ids: list[str]) -> dict[str, dict]` — 계약 trend 모양, 시계열 있는 장소만.

- [ ] **Step 1: 실패하는 테스트 작성** (모의 DB)
```python
def test_interest_drives_rank(self):
    sea = score_places(self.conn, goal(interests=["바다"]), S, I)
    self.assertEqual(sea[0]["category"] in I["interests"]["바다"]["categories"], True)
def test_quiet_pref_changes_weights_and_order(self):
    base = [p["place_id"] for p in score_places(self.conn, goal(interests=["바다"]), S, I)]
    quiet = [p["place_id"] for p in score_places(self.conn, goal(interests=["바다"], quiet_pref=True), S, I)]
    self.assertNotEqual(base, quiet)   # 모의 데이터는 이 차이가 나도록 지표를 배치한다
def test_missing_indicator_is_neutral_and_flagged(self):
    p = [x for x in score_places(self.conn, goal(), S, I) if x["indicators"]["nearby"]["missing"]][0]
    self.assertEqual(p["quiet"], 0.5)
def test_no_interest_means_all_one_and_tie_by_id(self):
    ps = score_places(self.conn, goal(), S, I)
    self.assertTrue(all(p["interest"] == 1.0 for p in ps))
    same = [p for p in ps if p["score"] == ps[0]["score"]]
    self.assertEqual([p["place_id"] for p in same], sorted(p["place_id"] for p in same))
def test_same_input_same_ranking(self):
    a = score_places(self.conn, goal(interests=["숲"]), S, I); b = score_places(self.conn, goal(interests=["숲"]), S, I)
    self.assertEqual([p["place_id"] for p in a], [p["place_id"] for p in b])
def test_region_and_nearby_indicators_are_separate_keys(self):
    p = score_places(self.conn, goal(), S, I)[0]
    self.assertEqual(p["indicators"]["region"]["source_id"], "563"); self.assertEqual(p["indicators"]["nearby"]["source_id"], "1208")
```
(`goal(**kw)`는 테스트 헬퍼: 계약 Goal 기본값 `days=3, interests=[], quiet_pref=False`, 나머지 None.)
- [ ] **Step 2: 실패 확인** — `PYTHONPATH=src python -m unittest tests.test_tools_places -v` → FAIL
- [ ] **Step 3: 구현**
- [ ] **Step 4: 통과 확인** → PASS
- [ ] **Step 5: Commit** — `git commit -m "feat(a): 장소 점수·탐색·지역 지표 Tool"`

---

### Task 8: Tool — 거리 계산 · 일정 생성

**Files:**
- Create: `src/malttara/tools/route.py`, `src/malttara/tools/itinerary.py`
- Test: `tests/test_tools_itinerary.py`

**Interfaces:**
- Consumes: `search_places`, `haversine_km`, 설정
- Produces:
  - `calculate_route(itinerary: dict, places: dict[str, dict]) -> list[dict]` — 계약 Route, 소수 1자리 반올림.
  - `pace_k(goal: dict, settings: dict) -> int` — pace None이면 `default_pace`.
  - `order_nearest(place_ids: list[str], places: dict, start: tuple[float, float] | None) -> list[str]` — start 없으면 첫 원소(최고점)부터, 있으면 start에 가장 가까운 장소부터 최근접 이웃.
  - `resolve_origin(conn, origin: str | None, prefixes) -> tuple[float, float] | None` — 정규화 이름이 같은 장소의 좌표, 없으면 None(→ 로그에 "출발지 위치 확인 불가, 미반영").
  - `create_itinerary(candidates: list[dict], slot_candidates: dict[str, list[dict]], goal: dict, settings: dict, origin_xy=None, region_order: list[str] | None = None) -> dict` — 설계 6.3:
    1. k = `pace_k`. 권역별 상위 k개 점수 합으로 권역 정렬(동점은 `region_order`=regions.json 순서), 상위 `days`개를 1일차부터 배정. 후보 있는 권역 수 < days면 권역 목록을 순환.
    2. 각 날짜: 그 권역 미사용 후보 상위 (k − 그날 slot 수)개 + slot 관심사마다 그 권역 slot 후보 최고점 1곳(없으면 생략, 그 자리는 일반 후보로 채움). `order_nearest` 후 slot 장소는 가운데(`len//2`)에 끼운다.
    3. 장소 중복 금지(전 일정).
    반환: 계약 Itinerary.

- [ ] **Step 1: 실패하는 테스트 작성**
```python
def test_k_per_pace_and_one_region_per_day(self):
    it = make(goal(days=2, pace="여유롭게"))
    self.assertTrue(all(len(d["place_ids"]) == 3 for d in it["days"]))
    for d in it["days"]:
        self.assertEqual({P[i]["region_id"] for i in d["place_ids"]}, {d["region_id"]})
def test_no_duplicates_and_cycle_when_few_regions(self):
    it = make(goal(days=6, pace="보통"))   # 모의 권역 4개 < 6일
    ids = [i for d in it["days"] for i in d["place_ids"]]
    self.assertEqual(len(ids), len(set(ids)))
def test_food_slot_one_per_day_in_middle(self):
    it = make(goal(days=2, pace="보통", interests=["바다", "음식"]))
    for d in it["days"]:
        cats = [P[i]["category"] for i in d["place_ids"]]
        self.assertEqual(cats.count("음식점"), 1); self.assertEqual(cats.index("음식점"), len(cats) // 2)
def test_route_totals(self):
    r = calculate_route({"days": [{"day": 1, "region_id": "x", "place_ids": ["a", "b", "c"]}]}, PTS)
    self.assertEqual(r[0]["total_km"], round(sum(r[0]["legs_km"]), 1))
```
- [ ] **Step 2: 실패 확인** — `PYTHONPATH=src python -m unittest tests.test_tools_itinerary -v` → FAIL
- [ ] **Step 3: 구현**
- [ ] **Step 4: 통과 확인** → PASS
- [ ] **Step 5: Commit** — `git commit -m "feat(a): 거리 계산, 일정 생성 Tool"`

---

### Task 9: Tool — 검증 · 수정(규칙·행동 적용) · 오류 주입

**Files:**
- Create: `src/malttara/tools/validate.py`, `src/malttara/tools/revise.py`
- Test: `tests/test_tools_validate.py`

**Interfaces:**
- Consumes: `calculate_route`, `order_nearest`, `centroid`, `pace_k`
- Produces:
  - `validate_itinerary(itinerary, places: dict, goal, settings, origin_xy=None) -> list[dict]` — 계약 Violation, 설계 6.4 순서: `distance`(total_km > max_daily_km), `regions`(그날 서로 다른 region_id 수 > 상한: 빡빡하게 2, 그 외 1), `duplicate`(두 번째 등장, place_id 기록), `out_of_scope`(places에 없거나 in_scope 0), `count`(장소 수 ≠ k), `origin`(origin_xy 있고 1일차 첫 장소까지 > max_origin_km).
  - `ALLOWED_ACTIONS = ("replace", "reorder", "remove")`
  - `apply_action(itinerary, action: dict, candidates_by_region: dict[str, list[dict]], places: dict, pinned: set[str]) -> dict | None` — action `{type, day, place_id, replacement_id?}`. 검증: type ∈ ALLOWED_ACTIONS, day 존재, place_id가 그날에 있고 pinned 아님, replace면 replacement가 그날 권역의 미사용 후보. 실패하면 None. 성공하면 새 itinerary(원본 불변) — replace/remove 뒤 그날 `order_nearest` 재정렬, reorder는 재정렬만.
  - `rule_revision(itinerary, violations, candidates_by_region, places, pinned) -> dict | None` — 설계 6.5 폴백: 첫 `distance`/`regions` 위반 날짜에서, 그날 권역과 다른 권역 장소가 있으면 그중 하나, 없으면 그날 권역 장소 중심에서 가장 먼 장소(pinned 제외)를 그 권역 미사용 최고점으로 `replace`하는 action. `duplicate`면 두 번째 등장 장소를 replace. 고칠 수 없으면 None(`count` 등).
  - `inject_error(itinerary, scored: list[dict], places: dict, settings) -> tuple[dict, str]` — `settings["inject_example"]`이 있고 해당 장소가 쓰이지 않았으면 그것, 없으면 1일차 권역과 **다른** 권역 최고점 미사용 장소로 1일차 마지막 장소를 바꾼다. 반환 (새 일정, 넣은 place_id).

- [ ] **Step 1: 실패하는 테스트 작성**
```python
def test_injected_error_detected_then_fixed_by_rule(self):
    bad, pid = inject_error(GOOD, SCORED, P, S)
    v = validate_itinerary(bad, P, G, S)
    self.assertIn("regions", {x["type"] for x in v})
    act = rule_revision(bad, v, CANDS, P, set())
    fixed = apply_action(bad, act, CANDS, P, set())
    self.assertNotIn(pid, fixed["days"][0]["place_ids"])
    self.assertNotIn("regions", {x["type"] for x in validate_itinerary(fixed, P, G, S)})
def test_distance_violation_over_60(self):
    v = validate_itinerary(FAR_DAY, P_FAR, G, S)
    self.assertEqual([x for x in v if x["type"] == "distance"][0]["limit"], 60)
def test_apply_action_rejects_unknown_or_pinned_or_foreign_replacement(self):
    self.assertIsNone(apply_action(GOOD, {"type": "teleport", "day": 1, "place_id": FIRST}, CANDS, P, set()))
    self.assertIsNone(apply_action(GOOD, {"type": "remove", "day": 1, "place_id": FIRST}, CANDS, P, {FIRST}))
    self.assertIsNone(apply_action(GOOD, {"type": "replace", "day": 1, "place_id": FIRST, "replacement_id": OTHER_REGION_ID}, CANDS, P, set()))
def test_count_violation_not_fixable(self):
    v = [{"day": 1, "type": "count", "value": 2, "limit": 4, "place_id": None}]
    self.assertIsNone(rule_revision(GOOD, v, CANDS, P, set()))
```
- [ ] **Step 2: 실패 확인** — `PYTHONPATH=src python -m unittest tests.test_tools_validate -v` → FAIL
- [ ] **Step 3: 구현**
- [ ] **Step 4: 통과 확인** → PASS
- [ ] **Step 5: Commit** — `git commit -m "feat(a): 일정 검증, 수정 행동, 오류 주입"`

---

### Task 10: Tool — 목표 해석(규칙) · 목표 검증

**Files:**
- Create: `src/malttara/tools/goal.py`
- Test: `tests/test_tools_goal.py`

**Interfaces:**
- Consumes: `interests.json`
- Produces:
  - `parse_goal_rules(text: str, interests_cfg: dict) -> dict` — 계약 Goal. 규칙: `(\d+)박\s*(\d+)일` → nights, days / `당일` → 0, 1 / `(\d+)일` 단독 → days=N, nights=N−1. pace: "여유"→여유롭게, "빡빡|알차게|최대한 많이"→빡빡하게, "보통"→보통, 없으면 None. interests: triggers 부분 문자열(설정 순서). quiet_pref: quiet_triggers. transport: "렌터카|렌트|차로"→렌터카, "버스|대중교통"→버스, "걸어|도보"→도보. companion: "아이|아기"→"아이와 함께", "부모님"→"부모님과 함께", "혼자"→"혼자", "친구"→"친구와 함께", "연인|커플"→"연인과 함께". month: `(\d{1,2})월`. origin: `(\S+)에서 출발` 또는 `숙소는 (\S+)`. `evidence`에 매칭된 원문 구간.
  - `validate_goal(goal: dict) -> list[str]` — `days` 없음 → `"days"`, days < 1 또는 > 7 → `"days_range"`, nights ≠ days−1 → nights를 고친 값으로 보정하고 오류는 아님. 반환: 누락·오류 코드 목록.
  - `merge_goal(llm_goal: dict | None, rule_goal: dict, text: str) -> dict` — LLM 결과의 각 값이 원문에 근거(evidence 구간이 text 안에 있음)가 있을 때만 채택, 아니면 규칙값. interests는 설정 키만 남긴다.

- [ ] **Step 1: 실패하는 테스트 작성** (테스트 프로필 3종, 기획 v0 6.2)
```python
def test_profile1(self):
    g = parse_goal_rules("2박 3일 동안 바다를 보며 여유롭게 쉬고, 현지 음식도 먹고 싶어요", I)
    self.assertEqual((g["nights"], g["days"], g["pace"]), (2, 3, "여유롭게"))
    self.assertEqual(g["interests"], ["바다", "음식"]); self.assertIsNone(g["transport"]); self.assertIsNone(g["origin"])
def test_profile2(self):
    g = parse_goal_rules("아이와 함께 1박 2일, 렌터카로 오름이랑 체험 위주로 다니고 싶어요", I)
    self.assertEqual((g["days"], g["transport"], g["companion"]), (2, "렌터카", "아이와 함께"))
    self.assertEqual(set(g["interests"]), {"오름", "체험·레저"})
def test_profile3_quiet(self):
    g = parse_goal_rules("혼자 3박 4일, 버스로 조용한 동네와 카페를 천천히 보고 싶어요", I)
    self.assertTrue(g["quiet_pref"]); self.assertEqual(g["transport"], "버스"); self.assertIn("카페", g["interests"])
def test_missing_and_range(self):
    self.assertEqual(validate_goal(parse_goal_rules("바다 보고 싶어요", I)), ["days"])
    self.assertEqual(validate_goal(parse_goal_rules("10박 11일", I)), ["days_range"])
def test_merge_rejects_unfounded_llm_value(self):
    rule = parse_goal_rules("2박 3일 바다", I)
    llm = dict(rule, origin="김포", evidence={"origin": "김포공항"})
    self.assertIsNone(merge_goal(llm, rule, "2박 3일 바다")["origin"])
```
- [ ] **Step 2: 실패 확인** — `PYTHONPATH=src python -m unittest tests.test_tools_goal -v` → FAIL
- [ ] **Step 3: 구현**
- [ ] **Step 4: 통과 확인** → PASS
- [ ] **Step 5: Commit** — `git commit -m "feat(a): 목표 해석 규칙, 목표 검증"`

---

### Task 11: LLM 클라이언트 · 판단 래퍼 · 결정 기록

**Files:**
- Create: `src/malttara/agent/__init__.py`, `src/malttara/agent/schema_lite.py`, `src/malttara/agent/llm.py`, `src/malttara/agent/decide.py`
- Test: `tests/test_agent_llm.py`

**Interfaces:**
- Produces:
  - `check_schema(obj, schema: dict) -> bool` — 지원: `type`(object/array/string/integer/number/boolean/null, 리스트 허용), `properties`, `required`, `enum`, `items`, `minimum`, `maximum`, `additionalProperties: false`.
  - `class LLMClient(api_key: str | None, base_url: str | None, model: str | None, timeout_s: float, transport: Callable[[str, dict, bytes, float], bytes] | None = None)` — `available -> bool`(키·주소·모델 모두 있을 때), `chat_json(system: str, user: str, schema: dict) -> dict | None`. OpenAI 호환 `POST {base_url}/chat/completions`, `response_format={"type": "json_schema", "json_schema": {"name": "out", "schema": schema, "strict": true}}`, temperature 0. 예외·HTTP 오류·JSON 파싱 실패·스키마 불일치 → None. 기본 transport는 `urllib.request`. 키를 로그에 남기지 않는다.
  - 개발용 K-EXAONE 2.5(`https://api.exaone.ai/v1`, 모델 `k-exaone_v2.5`)는 공식 문서에 `response_format`이 없고 항상 추론(`reasoning_content`)을 한다. 그래서 `LLMClient`에 `json_mode: "schema" | "prompt"`를 둔다. `"prompt"`면 `response_format` 없이 시스템 프롬프트 끝에 스키마를 붙여 "JSON만 출력"을 지시하고, `message.content`에서 첫 `{`~마지막 `}`를 잘라 파싱한 뒤 `check_schema`. `"schema"` 요청이 HTTP 400이면 같은 호출을 `"prompt"`로 한 번 재시도. `extra_body: dict`(예: EXAONE `{"reasoning_effort": "low"}`)를 요청 본문에 병합. `reasoning_content`는 무시한다.
  - `client_from_env(env: dict, settings: dict) -> LLMClient` — `LLM_JSON_MODE`(기본 `schema`), `LLM_EXTRA_BODY`(JSON 문자열, 기본 `{}`)를 읽는다.
  - `decide(conn, batch_id: str, point: str, llm: LLMClient, system: str, user: str, schema: dict, accept: Callable[[dict], bool], fallback: Callable[[], dict], options: object = None) -> tuple[dict, str]` — `llm.available`이면 `chat_json` → `accept(out)`이 참이면 `(out, "llm")`, 아니면 `(fallback(), "rule")`. 어느 쪽이든 `agent_decisions`에 (point, actor, options, choice, reason="llm_unavailable"|"llm_invalid"|"accepted") 기록.
  - `polish_text(llm, template: str) -> tuple[str, str]` — LLM에 문장 다듬기 요청. 출력의 모든 숫자 토큰(`\d+(\.\d+)?`)이 template에 있어야 채택, 아니면 `(template, "rule")`.

- [ ] **Step 1: 실패하는 테스트 작성** (가짜 transport)
```python
def fake(body): return lambda url, h, b, t: json.dumps({"choices": [{"message": {"content": json.dumps(body)}}]}).encode()
def test_no_key_uses_rule_without_network(self):
    called = []
    llm = LLMClient(None, None, None, 5, transport=lambda *a: called.append(1))
    out, actor = decide(self.conn, "A-x", "revise", llm, "s", "u", SCHEMA, lambda o: True, lambda: {"type": "reorder"})
    self.assertEqual((actor, called), ("rule", []))
def test_invalid_json_or_schema_falls_back(self):
    llm = LLMClient("k", "http://x", "m", 5, transport=fake({"type": 3}))
    self.assertEqual(decide(self.conn, "A-x", "revise", llm, "s", "u", SCHEMA, lambda o: True, lambda: {"type": "reorder"})[1], "rule")
def test_rejected_by_accept_falls_back_and_is_recorded(self):
    llm = LLMClient("k", "http://x", "m", 5, transport=fake({"type": "teleport"}))
    decide(self.conn, "A-x", "revise", llm, "s", "u", {"type": "object"}, lambda o: o["type"] in ALLOWED_ACTIONS, lambda: {"type": "reorder"})
    row = self.conn.execute("select actor, reason from agent_decisions").fetchone()
    self.assertEqual((row["actor"], row["reason"]), ("rule", "llm_invalid"))
def test_prompt_json_mode_parses_json_inside_text(self):
    body = {"choices": [{"message": {"content": "결과입니다:\n{\"type\": \"reorder\"}\n끝", "reasoning_content": "..."}}]}
    llm = LLMClient("k", "http://x", "m", 5, json_mode="prompt", transport=lambda u, h, b, t: json.dumps(body).encode())
    self.assertEqual(llm.chat_json("s", "u", {"type": "object", "properties": {"type": {"enum": ["reorder"]}}, "required": ["type"]}), {"type": "reorder"})
def test_polish_rejects_new_numbers(self):
    llm = LLMClient("k", "http://x", "m", 5, transport=fake({"text": "만족도 99%입니다"}))
    self.assertEqual(polish_text(llm, "직선 12.1 km"), ("직선 12.1 km", "rule"))
```
- [ ] **Step 2: 실패 확인** — `PYTHONPATH=src python -m unittest tests.test_agent_llm -v` → FAIL
- [ ] **Step 3: 구현**
- [ ] **Step 4: 통과 확인** → PASS
- [ ] **Step 5: Commit** — `git commit -m "feat(a): LLM 클라이언트, 판단 래퍼, 결정 기록"`

---

### Task 12: 작업 계획 · 설명 · 퀘스트 · Batch A 오케스트레이터

**Files:**
- Create: `src/malttara/agent/planner.py`, `src/malttara/agent/state.py`, `src/malttara/agent/batch_a.py`, `src/malttara/tools/quests.py`, `src/malttara/tools/explain.py`
- Test: `tests/test_batch_a.py`

**Interfaces:**
- Consumes: Task 7~11 전부
- Produces:
  - `plan_tasks_rules(goal: dict, has_trend_candidates: bool) -> list[dict]` — 설계 6.3.1 표를 그대로: 항목 `{"tool": str, "action": "add"|"skip", "reason": str, "params": dict}`. 필수 단계는 포함하지 않는다(코드가 고정).
  - `PLAN_SCHEMA: dict`, `accept_plan(out: dict) -> bool` — tool은 `{"search_slot", "get_region_data", "analyze_tourism", "check_data_quality", "origin_check", "expand_regions"}`만, params 키 제한.
  - `class BatchState(kind: str, now: datetime, prev_batch_id: str | None = None)` (state.py): 생성 시 `batch_id = new_batch_id(kind, now)`(`"A-MMDD-HHMMSS"`, 같은 초 충돌 시 `-2` 접미), `emit(tool, actor, status, message) -> None`(seq 증가, 메모리 리스트 + 스레드 안전), `events_after(n) -> list[dict]`, `finish(result) / fail(error)`, `save(conn)`(batches 테이블).
  - `generate_quests(itinerary, places) -> list[dict]` — 라벨: 이름에서 괄호 부분 제거, 공백 앞뒤 정리, 12자 초과면 첫 어절(어절이 12자 초과면 앞 12자). 계약 quests 모양.
  - `explain_place(place: dict, goal: dict, interests_cfg: dict) -> list[str]` — 템플릿 문장: 관심사 일치("관심사 '바다' ↔ 분류 '해수욕장' 일치" / 미반영이면 "관심사 미반영"), 읍면동 지표("{emd} 지표: 방문/거주 비율 {visit_ratio:.2f}, 범위 내 하위 {100−pct×100:.0f}% (563, {period})"), 반경 지표("장소 반경 {radius}km 렌터카 체류 {n}건 (1208, {period})"), 없으면 "지표 없음". slot 장소는 "TourAPI 등록 음식점/카페". "이 장소는 한적하다" 같은 평가 문장 금지.
  - `summary_template(result: dict) -> str` — 날짜별 권역·장소 수·직선 합계, 미반영 조건 목록.
  - `export_travel_plan(result: dict) -> str` — 인쇄용 HTML(인라인 CSS, 외부 자원 없음): 일정, 장소별 근거, 직선거리 표기 문구, 데이터 출처 표(`data_sources`), 미반영 조건.
  - `run_batch_a(conn, goal: dict, inject: bool, llm: LLMClient, settings, interests_cfg, regions_cfg, state: BatchState) -> dict` — 순서(각 단계 `state.emit`):
    1. `validate_goal`(실패면 `state.fail`)
    2. `plan_tasks`: `decide(point="plan_tasks", fallback=plan_tasks_rules)` → 항목마다 `emit(tool, actor, "add"|"skip", reason)`
    3. `search_places`(일반, limit 200) + 계획에 slot 있으면 slot별 탐색, `get_region_data`/`analyze_tourism`/`check_data_quality`는 계획에 있을 때만 실행(없으면 skip 로그)
    4. 권역 후보 수 < k인 권역이 배정되면 `expand_regions`(regions.json `adjacent`)로 후보 추가, 로그
    5. `create_itinerary` → (inject면 `inject_error`, emit "오류 주입: …") → `calculate_route`
    6. 검증·수정 루프 최대 `max_revisions`회: 위반 없으면 종료. `decide(point="revise", accept=lambda a: apply_action(...) is not None, fallback=rule_revision…)` → 적용 → 재검증. 폴백도 None이면 루프 종료.
    7. 결과 조립: 계약 BatchResult(`alternatives`: 같은 권역 미사용 상위 2개, `explanations`, `quests`, `quality`, `summary=polish_text(summary_template)`), `save_agent_state` = `state.save(conn)`.
- [ ] **Step 1: 실패하는 테스트 작성** (모의 DB, LLM 없음)
```python
def run(goal, inject=False):
    st = BatchState("A", datetime(2026, 11, 16, 19, 39, 16))
    res = run_batch_a(self.conn, goal, inject, NO_LLM, S, I, R, st); return res, st.events_after(0)
def test_profiles_produce_different_tool_plans(self):
    _, e1 = run(goal(days=3, pace="여유롭게", interests=["바다", "음식"]))
    _, e3 = run(goal(days=4, interests=["카페"], quiet_pref=True))
    plan = lambda ev: {(e["tool"], e["status"]) for e in ev if e["status"] in ("add", "skip")}
    self.assertIn(("search_slot", "add"), plan(e1)); self.assertIn(("get_region_data", "add"), plan(e3))
    self.assertNotEqual(plan(e1), plan(e3))
def test_inject_error_shows_fail_then_fix(self):
    res, ev = run(goal(days=2), inject=True)
    st = [e["status"] for e in ev if e["tool"] in ("validate_itinerary", "revise_itinerary")]
    self.assertIn("fail", st); self.assertIn("fix", st)
    self.assertFalse([v for v in res["violations_remaining"] if v["type"] == "regions"])
def test_result_shape_matches_contract(self):
    res, _ = run(goal(days=2))
    for k in ("batch_id", "itinerary", "places", "routes", "violations_remaining", "explanations", "summary", "quests", "alternatives", "quality"):
        self.assertIn(k, res)
    self.assertTrue(res["batch_id"].startswith("A-1116-193916"))
def test_all_actors_rule_without_llm(self):
    _, ev = run(goal(days=2))
    self.assertNotIn("llm", {e["actor"] for e in ev})
def test_explanations_never_claim_place_is_quiet(self):
    res, _ = run(goal(days=2, quiet_pref=True))
    self.assertFalse(any("한적" in s for ss in res["explanations"].values() for s in ss))
def test_too_few_candidates_leaves_count_violation_not_crash(self):
    res, _ = run(goal(days=2, pace="빡빡하게", interests=["카페"]))
    self.assertIsInstance(res["violations_remaining"], list)
```
- [ ] **Step 2: 실패 확인** — `PYTHONPATH=src python -m unittest tests.test_batch_a -v` → FAIL
- [ ] **Step 3: 구현** — LLM 프롬프트(시스템·사용자 메시지)는 `src/malttara/agent/prompts.py`에 상수로 모으고, 수치는 프롬프트에 근거로 넣되 출력 스키마에는 숫자 필드를 두지 않는다(place_id·enum만).
- [ ] **Step 4: 통과 확인** → PASS
- [ ] **Step 5: Commit** — `git commit -m "feat(a): 작업 계획, 설명, 퀘스트, Batch A"`

---

### Task 13: 피드백 · Batch B · 경로 비교

**Files:**
- Create: `src/malttara/tools/feedback.py`, `src/malttara/tools/compare.py`, `src/malttara/agent/batch_b.py`
- Test: `tests/test_batch_b.py`

**Interfaces:**
- Consumes: `user_interactions` 행, Batch A 결과(`batches.result_json`), Task 7~12
- Produces:
  - `record_event(conn, batch_id, place_id, type: str, value: str | None) -> None` — type ∈ `{"virtual_arrival", "feedback", "itinerary_add", "visited"}`, feedback value ∈ `{"interest", "must", "dislike"}`. 그 외 ValueError.
  - `analyze_feedback(events: list[dict], places: dict) -> dict` — 장소별 마지막 feedback, `{"pinned": set, "disliked": set, "liked_categories": {category: count}, "arrived": set}`. `virtual_arrival`은 선호 집계에 쓰지 않는다.
  - `rule_redesign(prev_itinerary, fb: dict, ...) -> dict` — 설계 6.7 규칙: must=고정, dislike=같은 권역 미사용 최고점으로 교체(재점수는 `boosts={cat: feedback_interest_boost}`), k보다 적은 날은 상위 장소 추가.
  - `REDESIGN_SCHEMA`, `accept_redesign(out, fb, prev) -> bool` — 각 place_id가 이전 일정에 있어야 함, must는 반드시 `pin`, dislike는 `keep`/`pin` 불가, decision ∈ `{"keep", "pin", "replace"}`.
  - `compare_itineraries(prev: dict, new: dict, fb: dict, replaced: dict[str, str]) -> list[dict]` — 계약 DiffItem. 이유 템플릿: pin "꼭 갈래요 → 고정", replace "별로예요 → 같은 권역 대안으로 교체" 또는 "검증 위반 → 교체", add "관심 분류 '{cat}' 선호 → 추가", remove "제외", keep "유지".
  - `run_batch_b(conn, prev_batch_id: str, llm, settings, interests_cfg, regions_cfg, state) -> dict` — 이전 결과·이벤트 로드 → `analyze_feedback` → `decide(point="redesign")` → 적용(code) → 검증·수정 루프(pinned는 교체 불가) → `compare_itineraries` → BatchResult(`kind="B"`, `prev_batch_id`, `diff`). 반응이 하나도 없으면 전부 keep으로 진행(원칙 4).

- [ ] **Step 1: 실패하는 테스트 작성**
```python
def test_must_pinned_dislike_replaced(self):
    a = run_a(goal(days=2)); d1 = a["itinerary"]["days"][0]["place_ids"]
    record_event(self.conn, a["batch_id"], d1[0], "feedback", "must")
    record_event(self.conn, a["batch_id"], d1[1], "feedback", "dislike")
    b = run_b(a["batch_id"])
    new_ids = [i for d in b["itinerary"]["days"] for i in d["place_ids"]]
    self.assertIn(d1[0], new_ids); self.assertNotIn(d1[1], new_ids)
    ch = {x["place_id"]: x["change"] for x in b["diff"]}
    self.assertEqual(ch[d1[0]], "pin"); self.assertEqual(ch[d1[1]], "replace")
    self.assertEqual(b["prev_batch_id"], a["batch_id"]); self.assertTrue(b["batch_id"].startswith("B-"))
def test_virtual_arrival_not_counted_as_preference(self):
    fb = analyze_feedback([{"place_id": "x", "type": "virtual_arrival", "value": None}], P)
    self.assertEqual((fb["pinned"], fb["disliked"], fb["liked_categories"]), (set(), set(), {}))
def test_no_feedback_keeps_everything(self):
    a = run_a(goal(days=2)); b = run_b(a["batch_id"])
    self.assertTrue(all(x["change"] in ("keep",) for x in b["diff"]))
def test_invalid_event_type_rejected(self):
    with self.assertRaises(ValueError): record_event(self.conn, "A-x", "p", "teleport", None)
```
- [ ] **Step 2: 실패 확인** — `PYTHONPATH=src python -m unittest tests.test_batch_b -v` → FAIL
- [ ] **Step 3: 구현**
- [ ] **Step 4: 통과 확인** → PASS
- [ ] **Step 5: Commit** — `git commit -m "feat(a): 피드백 분석, Batch B, 경로 비교"`

---

### Task 14: 표준 라이브러리 HTTP 서버

**Files:**
- Create: `src/malttara/server/__init__.py`, `src/malttara/server/routes.py`, `src/malttara/server/app.py`, `run.py`
- Test: `tests/test_server.py`

**Interfaces:**
- Consumes: 계약 2장 전부, Task 7~13
- Produces:
  - `make_server(db_path: str, map_path: str, static_dir: str, host: str, port: int, env: dict) -> ThreadingHTTPServer` — 요청마다 새 `sqlite3` 연결(`check_same_thread` 문제 회피). 배치는 `threading.Thread(daemon=True)`로 실행, `BatchState`를 메모리 dict에 보관.
  - 라우트 표 `ROUTES: list[tuple[str, re.Pattern, Callable]]` — 계약의 모든 경로. JSON 본문 검증 `require(body: dict, spec: dict[str, type | tuple]) -> str | None`(오류 메시지).
  - 정적 파일: `static_dir`(=`web/dist`) 아래만, 경로 탈출(`..`) 차단, 없는 경로는 `index.html`, `Content-Type`은 `mimetypes`. `static_dir`가 없으면 `/`에 "프론트 빌드 없음" 안내 HTML.
  - `/api/goal/parse`: `parse_goal_rules` → `llm.available`이면 `chat_json(GOAL_SCHEMA)` → `merge_goal` → `validate_goal`. 판단은 `agent_decisions`에 `batch_id="parse"`, `point="parse_goal"`로 기록. 응답 `actor`는 merge에서 LLM 값이 하나라도 채택되면 `"llm"`.
  - `/api/batch/a`: 본문 goal에 `validate_goal` 오류가 있으면 400(배치 시작 안 함).
  - 계약 보완(PR #2) 반영: `GET /api/config`(`{"interests": [{"key", "slot"}], "regions": [{"region_id", "name"}], "max_days": 7}`), `GET /api/stats/emd?month=all`(월 1~12 묶음), 없는 batch id 404, 오류 `error`는 한국어 문장, `seq`는 배치마다 1부터·`after=N`은 `seq > N`, BatchResult `places`에 일정 + alternatives + diff(`place_id`·`replaced_by`) 장소 전부. 정적 파일 `Content-Type` 고정 표: `.html` `text/html; charset=utf-8`, `.js` `text/javascript`, `.css` `text/css`, `.json` `application/json`, `.svg` `image/svg+xml`, `.woff2` `font/woff2`, `.png` `image/png`(`mimetypes` 사용 금지).
  - `run.py`: `.env` 로드 → `data/db/malttara.sqlite` 없으면 안내 메시지 후 종료 코드 1 → 서버 시작 → `webbrowser.open("http://127.0.0.1:8765/")`. `--mock` 옵션이면 임시 폴더에 `build_mock_db`로 만든 DB 사용(프론트 개발·시연용).

- [ ] **Step 1: 실패하는 테스트 작성** (모의 DB, 임의 포트 스레드 서버, `urllib`로 호출)
```python
def test_health_and_parse(self):
    self.assertTrue(get("/api/health")["ok"])
    r = post("/api/goal/parse", {"text": "2박 3일 바다 여유롭게"})
    self.assertEqual(r["goal"]["days"], 3); self.assertEqual(r["missing"], [])
def test_parse_missing_days(self):
    self.assertEqual(post("/api/goal/parse", {"text": "바다"})["missing"], ["days"])
def test_bad_json_is_400(self):
    self.assertEqual(post_raw("/api/goal/parse", b"{not json").status, 400)
def test_batch_a_rejects_goal_without_days(self):
    self.assertEqual(post_raw("/api/batch/a", json.dumps({"goal": dict(GOAL, days=None, nights=None), "inject_error": False}).encode()).status, 400)
def test_batch_a_poll_until_done(self):
    bid = post("/api/batch/a", {"goal": GOAL, "inject_error": True})["batch_id"]
    r = poll(bid)   # 500ms 간격, 최대 20초
    self.assertTrue(r["done"]); self.assertIsNotNone(r["result"]); self.assertTrue(r["events"])
def test_events_and_batch_b(self):
    a = poll(post("/api/batch/a", {"goal": GOAL, "inject_error": False})["batch_id"])["result"]
    pid = a["itinerary"]["days"][0]["place_ids"][0]
    self.assertTrue(post("/api/events", {"batch_id": a["batch_id"], "place_id": pid, "type": "feedback", "value": "dislike"})["ok"])
    b = poll(post("/api/batch/b", {"prev_batch_id": a["batch_id"]})["batch_id"])["result"]
    self.assertEqual(b["prev_batch_id"], a["batch_id"])
def test_config_and_month_all(self):
    c = get("/api/config"); self.assertEqual(c["max_days"], 7); self.assertEqual(len(c["regions"]), 4)
    self.assertEqual(sorted(get("/api/stats/emd?month=all")["months"].keys(), key=int), [str(m) for m in range(1, 13)])
def test_unknown_batch_404_and_js_mime(self):
    self.assertEqual(get_raw("/api/batch/A-0000-000000/events?after=0").status, 404)
    self.assertEqual(get_raw("/assets/app.js").headers["Content-Type"], "text/javascript")   # 픽스처 static_dir에 assets/app.js
def test_static_traversal_blocked(self):
    self.assertNotIn(b'"weights"', get_raw("/../config/settings.json").read())   # 설정 파일 내용이 새면 안 됨
def test_print_is_html_without_external_urls(self):
    a = poll(post("/api/batch/a", {"goal": GOAL, "inject_error": False})["batch_id"])["result"]
    html = get_raw("/api/print/" + a["batch_id"]).read().decode()
    self.assertIn("<html", html); self.assertNotIn("http://", html.replace("http://127.0.0.1", ""))
```
- [ ] **Step 2: 실패 확인** — `PYTHONPATH=src python -m unittest tests.test_server -v` → FAIL
- [ ] **Step 3: 구현**
- [ ] **Step 4: 통과 확인** → PASS
- [ ] **Step 5: 수동 확인** — Run: `PYTHONPATH=src python run.py --mock` → Expected: 브라우저가 열리고 `/api/health`가 `{"ok": true, …}`.
- [ ] **Step 6: Commit** — `git commit -m "feat(a): 표준 라이브러리 HTTP 서버, run.py"`

---

### Task 15: 실행 스크립트 · 테스트 10종 · 클린 설치 검증

**Files:**
- Create: `run.bat`, `tests/test_acceptance.py`, `docs/05_submission/manual_run.md`(설치·실행 매뉴얼 초안, B 트랙이 다듬음)
- Modify: `docs/05_submission/README.md`(명시 사항 표: Python 버전, ETL 패키지)

**Interfaces:**
- Consumes: 전 Task
- Produces: `run.bat` — `py -3.11` 또는 `python`을 찾아 `set PYTHONPATH=src` 후 `run.py` 실행, Python이 없으면 python.org 설치 안내를 출력하고 `pause`.

- [ ] **Step 1: 테스트 10종 작성** (기획 v0 6.1, 실제 DB가 있으면 실제 DB, 없으면 모의 DB)
```python
class Acceptance(unittest.TestCase):
    def test_01_preference_changes_result(self): ...      # 관심사 바다 vs 숲 → 1일차 장소 집합이 다름
    def test_02_same_input_same_result(self): ...          # 같은 goal 두 번 → itinerary 동일
    def test_03_rejection_gives_alternative(self): ...     # dislike → Batch B에서 같은 권역 다른 장소
    def test_04_indicator_change_changes_rank(self): ...   # 임시 DB에서 한 장소 quiet_count를 최댓값으로 → quiet_pref 순위 하락
    def test_05_missing_data_safe(self): ...               # emd_stats 비운 DB → 배치 완료, quality.no_region_indicator > 0
    def test_06_llm_failure_still_works(self): ...         # transport가 예외 → 전 판단 actor == "rule", 결과 있음
    def test_07_offline_rule_mode(self): ...               # LLM 키 없음 → 동일하게 완료
    def test_08_game_and_list_same_analysis(self): ...     # 같은 batch 결과에서 quests의 place_id 순서 == itinerary 순서
    def test_09_sources_and_period_visible(self): ...      # 모든 장소 indicators에 source_id·period(또는 missing) 있음, print HTML에 "563"·"1208" 포함
    def test_10_virtual_vs_visited_separate(self): ...     # virtual_arrival과 visited 기록 → type별로 따로 조회됨, 선호 집계에는 미반영
```
각 메서드 본문은 주석의 조건을 assert로 쓴다(Task 12·13 헬퍼 재사용).
- [ ] **Step 2: 실행** — Run: `PYTHONPATH=src python -m unittest discover -s tests -v` → Expected: 전부 PASS
- [ ] **Step 3: 실행 중 코드가 표준 라이브러리만 쓰는지 테스트** — `tests/test_acceptance.py`에 추가:
```python
    def test_11_runtime_imports_stdlib_only(self):
        files = [f for f in pathlib.Path("src/malttara").rglob("*.py") if "etl" not in f.parts or f.name in ("mock_data.py", "__init__.py")] + [pathlib.Path("run.py")]
        bad = set()
        for f in files:
            for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
                names = [a.name for a in node.names] if isinstance(node, ast.Import) else [node.module or ""] if isinstance(node, ast.ImportFrom) and node.level == 0 else []
                bad |= {n.split(".")[0] for n in names if n and n.split(".")[0] not in sys.stdlib_module_names and n.split(".")[0] != "malttara"}
        self.assertEqual(bad, set())
```
Run: `PYTHONPATH=src python -m unittest tests.test_acceptance -v` → Expected: 11개 PASS (`etl/mock_data.py`와 `etl/__init__.py`는 `run.py --mock`이 import하므로 검사 대상에 포함한다)
- [ ] **Step 4: 클린 설치 검증** — Python 3.11(python.org 설치본)만 있는 Windows 환경(가능하면 다른 PC 또는 새 사용자 계정)에서 ZIP을 풀고 `run.bat` 더블클릭 → 브라우저에서 프로필 1로 01→04 완주. LLM 키 없이 한 번, 있을 때 한 번. 결과를 `manual_run.md`의 "검증 기록"에 날짜와 함께 적는다.
- [ ] **Step 5: Commit** — `git commit -m "test(a): 테스트 10종, 실행 스크립트, 설치 매뉴얼 초안"`
