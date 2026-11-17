# 말따라 제주 — 프론트(B) 요구 명세: 기능 · API · 데이터 양식

- 작성: 2026-11-17, B 트랙
- 대상: A 트랙(데이터·에이전트·서버)
- 기준 문서: 계약 `2026-11-16-api-contract.md`, B 계획 `2026-11-16-track-b-frontend.md`, A 계획 `2026-11-16-track-a-data-agent.md`, 설계 7장
- 이 문서의 역할: 프론트가 **어떤 화면에서 어떤 API의 어떤 필드를 어떻게 쓰는지**를 한곳에 모은다. 계약을 바꿔야 하는 항목은 4장에 정리했고, 같은 PR에서 계약 문서도 고쳤다(계약 변경 PR이라 A 확인 필요).

---

## 1. 화면별 기능 명세

### 공통 (앱 셸)
| 기능 | 동작 | API |
|---|---|---|
| 앱 시작 | 서버 상태·LLM 사용 가능 여부 확인. LLM 없으면 헤더에 `규칙 모드` 표시 | `GET /api/health` |
| 설정 불러오기 | 관심사 칩 목록, 권역 이름, 기간 선택 범위 | `GET /api/config` **(신규 제안, 4장 C2)** |
| [처음부터] | 진행 중 폴링 중단, 상태 초기화. 이전 배치 응답이 늦게 와도 무시(session_id). 서버 호출 없음 | — |
| 단계 탭 | 01~04, 아직 못 가는 단계는 비활성 | — |

### 01 여행 설명 + 조건 확인
| 기능 | 동작 | API · 사용 필드 |
|---|---|---|
| 한 줄 입력 | 여러 줄 입력창, 예시 문장 버튼 3개(입력창에 채움) | — |
| 조건 해석 | [조건 확인하기] → 칩 줄 표시. `해석: AI`/`해석: 규칙` 배지 | `POST /api/goal/parse` → `goal`, `missing`, `actor` |
| 조건 칩 | 기간·여유·관심·한적함·이동수단·동행·출발지·날짜. 값이 `null`이면 `(미반영)`. pace null → `여유 (미반영·보통 기준 적용)`, 동행 값 뒤 `(점수 미반영)` | `goal.*` |
| 칩 편집 | 기간 1~N일, 여유 3택+미반영, 관심 다중 선택(설정 키), 이동수단 3택+미반영, 월 1~12+미반영, 동행·출발지 텍스트 | `GET /api/config`의 `interests`, `max_days` |
| 기간 필수 | `missing`에 `days` → 기간 칩 경고색 + 안내 문구, [경로 만들기] 비활성 | `missing` |
| 데이터 지도 | 읍면동별 방문/거주 비율 백분위로 색칠, 범례 `읍면동별 방문/거주 비율 · 출처 563 · {period}`, 설명 `읍면동 단위 통계입니다. 개별 장소의 혼잡도가 아닙니다.` 값 null은 빗금 + `지표 없음` | `GET /api/map`, `GET /api/stats/emd?month={goal.month}` → `items[].emd`, `pct`, `period` |

### 02 경로 만들기 (Batch A)
| 기능 | 동작 | API · 사용 필드 |
|---|---|---|
| 배치 시작 | 화면 진입 시 1회. `오류 주입 시연` 토글 → [다시 만들기]로 재실행 | `POST /api/batch/a` `{goal, inject_error}` → `batch_id` |
| 실행 로그 | 500ms 폴링, 줄마다 상태 기호(✓✗↻＋−)·tool·주체 배지(AI/규칙/코드)·message. 자동 스크롤. 20초 넘으면 `시간이 걸리고 있습니다…`, `error`면 오류 + [다시 시도] | `GET /api/batch/{id}/events?after={마지막 seq}` → `events[]`, `done`, `result`, `error` |
| 지도 | 권역 경계, 날짜별 색 직선 연결선 + 순번 마커, 날짜 탭 | `/api/map` + `result.itinerary`, `result.places[].lat/lon` |
| 날짜 목록 | `{day}일차 · {권역 이름}` + `직선 {total_km} km (도로거리·이동시간 아님)` | `itinerary.days[]`, `routes[]`, 권역 이름은 `/api/config` 또는 `/api/map`의 `regions[].name` |
| 장소 카드 | 이름, 분류(`category ?? "분류 없음"`, `category_source`), 개요(3줄), 지표 블록 2개, 근거 문장, 대안 장소 이름 | `places[id]`, `explanations[id]`, `alternatives[id]` → **대안도 `places`에 들어 있어야 이름 표시 가능(C3)** |
| 지표 블록 | `{emd} 지표 (읍면동 단위)`: `방문/거주 비율 {visit_ratio:.2f} · 범위 내 백분위 {pct*100}` / `장소 반경 {radius_km}km 지표`: `렌터카 체류 {quiet_count}건 · 범위 내 백분위 {pct*100}`. 출처 줄 `{source_id} · {period}`. `missing` → `지표 없음` | `places[id].indicators.region/nearby` |
| 남은 위반 | 경고 상자. 종류별 한국어 문구(아래 3장 Violation) | `violations_remaining[]` |
| 요약·품질 | 요약 문단, `분류 없음 n곳 · 읍면동 지표 없음 n곳 · 반경 지표 없음 n곳` | `summary`, `quality` |

### 03 미리보기 (게임 / 목록)
| 기능 | 동작 | API · 사용 필드 |
|---|---|---|
| 모드 전환 | [게임 \| 목록], 안내 `게임은 선택입니다…` | — |
| 게임 | 날짜 탭 → 그 날 퀘스트 순서. `다음 목적지: {label}` 타이핑, IME 조합 중 판정 금지, 공백 무시 비교. 정답이면 말 이동 + 도착 카드, 틀리면 글자 수 힌트, [건너뛰기] | `result.quests[].items[]` (`place_id`, `label`) |
| 가상 도착 기록 | 정답 시 1회 | `POST /api/events` `{type: "virtual_arrival", value: null}` |
| 반응 | `관심` `꼭 갈래요` `별로예요`. 다시 누르면 같은 값, 다른 값이면 교체(서버는 마지막 값 사용) | `POST /api/events` `{type: "feedback", value: "interest"\|"must"\|"dislike"}` |
| 목록 | 날짜별 장소 카드 + 같은 버튼(가상 도착 이벤트 없음) | 같음 |
| [다시 짜기] | 반응 0개여도 진행 | — |

### 04 다시 짜기 + 최종 계획
| 기능 | 동작 | API · 사용 필드 |
|---|---|---|
| Batch B | 진입 시 1회, 로그 제목 `실행 로그 {B id} (이전 {A id})` | `POST /api/batch/b` `{prev_batch_id}` → 폴링 |
| 변경 전후 비교 | 날짜별 이전/이후 2열, 배지 `유지·고정·교체·추가·제외`, 교체는 `이전 → 이후`, 이유 | B `result.diff[]` + A `result.itinerary`. **제외·교체된 장소도 B `places`에 포함(C3)** |
| 최종 일정 | 02와 같은 지도·목록·카드(근거 패널) | B `result` |
| 차트 1 | 일정 읍면동들의 월별 visit_ratio, 제목 `일정 지역의 월별 방문/거주 비율 (읍면동 단위)`, 출처 `563 · {period}` | `GET /api/stats/emd?month=1..12` (12회, 캐시) — 또는 C9 일괄 조회 |
| 차트 2 | `has_trend` 장소별 내국인·외국인 입장객, 출처 `189·190 · {period}`. 없으면 `해당 장소의 입장객 통계 없음` | `GET /api/places/{id}/trend` |
| 인쇄 | 새 창으로 인쇄용 HTML | `GET /api/print/{batch_id}` |

---

## 2. 호출 순서 (한 사용자 기준)

```
앱 시작   GET /api/health, GET /api/config, GET /api/map, GET /api/stats/emd
01       POST /api/goal/parse  (칩 편집은 프론트에서만, 서버 호출 없음)
         goal.month가 바뀌면 GET /api/stats/emd?month=N
02       POST /api/batch/a → GET /api/batch/{A}/events?after=N (500ms, done까지)
03       POST /api/events (virtual_arrival / feedback, 여러 번)
04       POST /api/batch/b → GET /api/batch/{B}/events?after=N
         GET /api/stats/emd?month=1..12, GET /api/places/{id}/trend (has_trend인 장소)
         [인쇄] GET /api/print/{B}
```

---

## 3. 프론트가 필요한 데이터 양식 (필드별 사용처 · null 처리)

계약 1장 모양을 그대로 쓴다. 아래는 프론트가 **실제로 읽는 필드**와 값이 없을 때의 표시다. 여기 없는 필드는 프론트가 쓰지 않는다(빼도 된다는 뜻은 아님).

### Goal
| 필드 | 사용 | null/빈 값 표시 |
|---|---|---|
| `days`, `nights` | 기간 칩 `{nights}박 {days}일`(당일 `당일치기`) | `days` null → `(미반영)` + 경고, 버튼 비활성 |
| `pace` | 여유 칩 | `여유 (미반영·보통 기준 적용)` |
| `interests[]` | 관심 칩(`/api/config` 키) | `[]` → `관심 (미반영)` |
| `quiet_pref` | `한적함` 칩 | false → 칩 숨김 |
| `transport`, `companion`, `origin`, `month` | 각 칩 | `(미반영)` |
| `evidence` | 칩 툴팁(원문 구간) | 없으면 툴팁 없음 |
- 프론트가 칩을 편집하면 `nights = days - 1`로 맞추고, 바꾼 필드의 `evidence` 키는 지운다.

### Place
| 필드 | 사용 | null 표시 |
|---|---|---|
| `place_id`, `name` | 카드 제목, 마커, 퀘스트 | 필수 |
| `lat`, `lon` | 지도 마커·말 위치(`project`로 변환) | 필수 |
| `emd` | 지표 블록 제목 `{emd} 지표 (읍면동 단위)` | null → `읍면동 미상` |
| `region_id`, `region_name` | 권역 표시 | 필수 |
| `category`, `category_source` | 분류 | `분류 없음` |
| `overview` | 개요 3줄 | 숨김 |
| `score`, `interest`, `spread`, `quiet` | **표시하지 않음**(근거 문장은 `explanations`) | — |
| `indicators.region` | `visit_ratio`, `pct`, `period`, `source_id`, `missing` | `지표 없음` |
| `indicators.nearby` | `quiet_count`, `pct`, `radius_km`, `period`, `source_id`, `missing` | `지표 없음` |
| `has_trend` | 차트 2 대상 여부 | false → 통계 없음 문구 |

### Itinerary · Route · Violation
- `itinerary.days[]`: `day`, `region_id`, `place_ids[]`(순서 = 방문 순서).
- `routes[]`: `day`, `total_km`(표시), `legs_km[]`(구간별 거리 — 카드 사이에 작게 표시 예정).
- `violations_remaining[]` 문구:

| type | 문구 | value / limit |
|---|---|---|
| `distance` | `{day}일차 직선 합계 {value} km가 기준 {limit} km를 넘습니다` | km / km |
| `regions` | `{day}일차에 권역 {value}곳 방문(기준 {limit})` | 개수 / 개수 |
| `count` | `{day}일차 장소 {value}곳(목표 {limit}곳) — 조건에 맞는 장소가 부족합니다` | 개수 / 개수 |
| `origin` | `{day}일차 첫 장소가 출발지에서 직선 {value} km(기준 {limit} km)` | km / km |
| `duplicate` | `{day}일차 {장소명}이(가) 중복됩니다` | null / null, `place_id` 필수 |
| `out_of_scope` | `{day}일차 {장소명}은(는) 범위 밖 장소입니다` | null / null, `place_id` 필수 |

### LogEvent
- `seq`(1부터 증가), `tool`, `actor`(`llm`→`AI`, `rule`→`규칙`, `code`→`코드`), `status`(기호), `message`(한국어, 그대로 표시), `ts`(표시 안 함).

### BatchResult
- `batch_id`, `kind`, `prev_batch_id`, `itinerary`, `places`, `routes`, `violations_remaining`, `explanations`(문장 배열, 그대로 표시), `summary`, `quests`, `alternatives`, `quality`, `diff`.

### MapData (`GET /api/map`)
- `view_box`(`"0 0 W H"`), `emds[]`(`emd`, `region_id`, `d`), `regions[]`(`region_id`, `name`, `d`), `project`(`min_lon`, `max_lat`, `scale`).
- 투영: `x = (lon - min_lon) * scale * cos(33.4°)`, `y = (max_lat - lat) * scale` (A `build_map`과 동일).
- path 좌표는 소수 1자리면 충분(파일 크기). 권장 W ≈ 1000.

### EmdStats · Trend
- EmdStats: `period`, `source_id`, `items[]`(`emd`, `region_id`, `visit_ratio`, `pct`). `emd`는 MapData `emds[].emd`와 **같은 키**여야 색칠 가능(C1).
- Trend: `period`, `source_ids`, `series[]`(`year_month`, `domestic`, `foreign`, null 허용 → 선 끊김).

---

## 4. 계약 공백·불일치와 제안 (이 PR에서 계약 문서에 반영)

| # | 문제 | 제안 | 영향 |
|---|---|---|---|
| C1 | 읍면동 키 표기가 섞임: 계약 예시 `"emd": "애월읍"` vs A 계획 `"제주시 애월읍"`(parse_emd·regions.json·563 `emd_name`) | **모든 응답의 `emd`는 `"{시} {읍면동}"` 형식 하나로**(예: `"제주시 애월읍"`, `"서귀포시 서홍동"`). Place.emd, indicators.region.emd, map.emds[].emd, stats.items[].emd 동일 | 지도 색칠·지표 매칭 |
| C2 | 관심사 키·권역 이름·기간 범위를 프론트가 알 방법이 없음(관심 칩 편집 불가) | `GET /api/config` 신규: `{"interests": [{"key": "바다", "slot": false}, …], "regions": [{"region_id", "name"}], "max_days": 7}` — `config/interests.json`·`regions.json`·settings에서 그대로 | 01 칩 편집 |
| C3 | `alternatives`의 장소 id만 오고 이름이 없을 수 있음. Batch B에서 제외·교체된 장소 정보도 필요 | `BatchResult.places`에 **일정 장소 + alternatives 장소 + (B) diff에 나온 모든 place_id/replaced_by** 포함 | 카드 대안 이름, 04 비교 |
| C4 | `after=N` 의미 미정 | `seq`는 배치마다 1부터. `after=N` → `seq > N`만 반환. 처음은 `after=0` | 로그 중복·누락 |
| C5 | 계약 표는 `GET /, /assets/*`만 적혀 있음. 프론트는 `web/dist/fonts/*`(Pretendard)도 씀 | `web/dist` 아래 **모든 파일** 서빙(A 계획 Task 14와 동일하게 계약 문구 정리) | 글꼴 깨짐 |
| C6 | Windows의 Python `mimetypes`는 레지스트리를 읽어 `.js`를 `text/plain`으로 줄 때가 있음 → 브라우저가 모듈 스크립트를 거부해 **빈 화면** | 서버에 MIME 고정 표: `.js` `text/javascript`, `.css` `text/css`, `.woff2` `font/woff2`, `.svg` `image/svg+xml`, `.json` `application/json`, `.html` `text/html; charset=utf-8` | 센터 PC(Windows 11)에서 첫 화면 |
| C7 | 중산간·한라산 권역은 읍면동이 없어 `regions[].d`를 만들 수 없음 | `boxes`가 있으면 `regions[]`에 `mountain`을 넣고 `d`는 박스 다각형. 없으면(4권역 폴백) 넣지 않음. `emds[].region_id`는 해안 권역 그대로 | 지도 권역선 |
| C8 | Violation `duplicate`·`out_of_scope`의 `value`/`limit` 의미 미정 | 두 타입은 `value: null, limit: null`, `place_id` 필수 | 경고 문구 |
| C9 | (선택) 차트 1에 월별 통계 12회 호출 | `GET /api/stats/emd?month=all` → `{"period", "source_id", "months": {"1": [items], …, "12": [items]}}`. 없으면 프론트가 12회 호출(동작은 함) | 04 로딩 시간 |
| C10 | 오류 응답 경로 | 없는 batch id → 404 `{"error"}`, 잘못된 goal → 400 `{"error": "여행 기간이 없습니다"}`처럼 **사용자에게 그대로 보여줄 한국어 문장** | 오류 문구 |

---

## 5. 지도 경계 데이터 제안 (미결 사항 해소용)

`open-questions.md`의 "행정경계 GeoJSON 출처와 라이선스" 항목에 대한 B 조사 결과.

- 제주데이터허브에는 행정경계 폴리곤·DEM이 없다(카탈로그 1,259건 확인). 외부 필요.
- 제안: **`vuski/admdongkor` `ver20260701/HangJeongDong_ver20260701.geojson`**
  - 원자료: 통계청 SGIS 행정동 경계, **공공누리 제1유형**(출처표시, 상업 이용·변경·재배포 허용)
  - 가공본 데이터 라이선스: **CC BY 4.0** → 가공본 동봉 가능, 출처 표기 필수
  - 형식: GeoJSON, WGS84(EPSG:4326), 속성 `adm_nm`("제주특별자치도 제주시 애월읍"), `adm_cd`, `adm_cd2`
  - 제주 행정동 43개. `adm_nm`에서 "제주특별자치도 " 접두를 떼면 C1 키 형식과 같다. 부속섬 단위인 `제주시 추자면`, `제주시 우도면`은 제외 대상.
  - 필수 출처 문구(명시 사항 표와 매뉴얼에 그대로): "본 데이터는 통계청 통계지리정보서비스(SGIS, https://sgis.kostat.go.kr)에서 공공누리 제1유형으로 개방한 행정동 경계를 가공한 것이며(가공: vuski/admdongkor, https://github.com/vuski/admdongkor), CC BY 4.0으로 배포됩니다."
- 주의: 행정동 기준이다. 563 `emd_name`이 행정동인지 법정동인지는 A가 원본으로 확인(동 지역에서 차이 가능). 다르면 `emd_alias.csv`로 맞춘다.
- B는 같은 파일로 목업 `MapData` 픽스처를 만든다(계약 모양, 투영식 동일). A의 `build_map` 결과와 키가 같아야 목업→실서버 전환이 매끄럽다.

---

## 6. A에게 확인받고 싶은 것

1. C1~C10 수용 여부 (특히 C1 emd 키, C2 `/api/config`, C3 places 범위, C6 MIME).
2. 기간 선택 최대값(`max_days`) — 7일이면 충분한지.
3. 경계 데이터를 admdongkor로 확정해도 되는지(5장).
4. `python run.py --mock`(A Task 14) 예상 시점 — B는 그 전까지 `VITE_MOCK=1` 픽스처로 진행.
