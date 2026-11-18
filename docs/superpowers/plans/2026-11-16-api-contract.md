# 말따라 제주 — A·B 트랙 공용 계약 (데이터 모양 · HTTP API)

A 트랙(데이터·에이전트)과 B 트랙(프론트)이 함께 지키는 계약이다. 두 계획서(`2026-11-16-track-a-data-agent.md`, `2026-11-16-track-b-frontend.md`)가 이 문서를 참조한다. 바꿀 때는 두 트랙이 함께 바꾸고 이 문서를 먼저 고친다.

- 근거 설계: `docs/superpowers/specs/2026-11-16-malttara-jeju-design.md`
- 모든 JSON은 UTF-8, 키는 snake_case. "미반영"은 `null`로 보낸다(빈 문자열·기본값으로 채우지 않는다).
- 수치는 모두 서버(Tool) 결과다. 프론트는 수치를 계산하거나 만들지 않는다(표시용 반올림만).

## 1. 데이터 모양

### Goal (조건, 설계 6.1)
```json
{
  "nights": 2, "days": 3,
  "pace": "여유롭게",            // "여유롭게" | "보통" | "빡빡하게" | null
  "interests": ["바다", "음식"],  // config/interests.json의 키만. 없으면 []
  "quiet_pref": false,           // "조용한·한적한·덜 붐비는" 류 표현이 있으면 true
  "transport": null,             // "렌터카" | "버스" | "도보" | null
  "companion": null,             // 자유 문자열 | null
  "origin": null,                // 자유 문자열 | null
  "month": null,                 // 1~12 | null
  "evidence": {"days": "2박 3일", "pace": "여유롭게", "interests": "바다, 현지 음식"}
}
```
- `days`만 필수. `nights`는 `days - 1`로 맞춘다(당일치기 `nights: 0, days: 1`).

### Place (장소 카드)
```json
{
  "place_id": "p1349-00123", "name": "…", "lat": 33.4, "lon": 126.5,
  "emd": "제주시 애월읍", "region_id": "west", "region_name": "서부",
  "category": "해수욕장", "category_source": "tourapi",   // tourapi|hub_811|hub_812|hub_784|hub_858|keyword|none
  "overview": "…" ,                                         // TourAPI 개요, 없으면 null
  "source": "1349",                                          // "1349" | "tourapi"
  "score": 0.82, "interest": 1.0, "spread": 0.7, "quiet": 0.5,
  "indicators": {
    "region": {"emd": "제주시 애월읍", "visit_ratio": 3.21, "pct": 0.3, "period": "2018-01~2022-09", "month": null, "source_id": "563", "missing": false},
    "nearby": {"quiet_count": 412, "pct": 0.5, "radius_km": 1.0, "period": "2021-07~12 토요일", "source_id": "1208", "missing": false}
  },
  "has_trend": true
}
```
- **읍면동 키 `emd`는 모든 응답에서 `"{시} {읍면동}"` 한 형식**이다(예: `"제주시 애월읍"`, `"서귀포시 서홍동"`). Place.emd, indicators.region.emd, `GET /api/map`의 `emds[].emd`, `GET /api/stats/emd`의 `items[].emd`가 같은 키여야 한다.
- `indicators.region`은 **읍면동 지표**, `indicators.nearby`는 **장소 반경 지표**다. 화면은 둘을 다른 제목 아래 따로 그린다(원칙 3). 지표가 없으면 `missing: true`이고 값은 `null`.

### Itinerary
```json
{"days": [{"day": 1, "region_id": "west", "place_ids": ["p…", "p…", "p…"]}]}
```

### Route
```json
{"day": 1, "legs_km": [4.2, 7.9], "total_km": 12.1}
```
- 프론트 표기: `직선 12.1 km (도로거리·이동시간 아님)`.

### Violation
```json
{"day": 1, "type": "distance", "value": 71.3, "limit": 60, "place_id": null}
```
- `type`: `distance` | `regions` | `duplicate` | `out_of_scope` | `count` | `origin`.
- `distance`·`origin`은 km, `regions`·`count`는 개수. `duplicate`·`out_of_scope`는 `value: null, limit: null`이고 `place_id`가 반드시 있다.

### LogEvent (실행 로그 한 줄)
```json
{"seq": 3, "batch_id": "A-1116-193916", "tool": "validate_itinerary",
 "actor": "code", "status": "fail", "message": "2일차 직선 71.3km > 60km", "ts": "2026-11-16T19:39:18"}
```
- `seq`는 배치마다 1부터 1씩 증가한다.
- `actor`: `llm` | `rule` | `code`. `status`: `ok` | `fail` | `fix` | `skip` | `add`.
- `plan_tasks`가 Tool을 추가·생략하면 `status: "add"`/`"skip"`와 이유를 `message`에 남긴다.

### BatchResult
```json
{
  "batch_id": "A-1116-193916", "kind": "A", "prev_batch_id": null,
  "goal": {…Goal},
  "itinerary": {…Itinerary},
  "places": {"p…": {…Place}},
  "routes": [{…Route}],
  "violations_remaining": [{…Violation}],
  "explanations": {"p…": ["관심사 '바다' ↔ 분류 '해수욕장' 일치", "…"]},
  "summary": "…",                       // 설명 문단(LLM 다듬기 또는 템플릿)
  "quests": [{"day": 1, "items": [{"place_id": "p…", "label": "협재해수욕장"}]}],
  "alternatives": {"p…": ["p…", "p…"]}, // 같은 권역 대안 상위 2개
  "quality": {"no_category": 3, "no_region_indicator": 1, "no_nearby_indicator": 0},
  "diff": null                          // Batch B에서만: [{…DiffItem}]
}
```

- `places`에는 **일정 장소 + `alternatives`에 나온 장소 + (Batch B) `diff`의 `place_id`·`replaced_by` 전부**를 넣는다. 프론트는 이름·카드를 `places`에서만 찾는다.

### DiffItem (Batch B)
```json
{"place_id": "p…", "change": "replace", "replaced_by": "p…", "day": 2, "reason": "별로예요 → 같은 권역 대안으로 교체"}
```
- `change`: `keep` | `pin` | `replace` | `add` | `remove`.

## 2. HTTP API (Python 표준 라이브러리 서버, 기본 `http://127.0.0.1:8765`)

| 메서드·경로 | 요청 | 응답 |
|---|---|---|
| `GET /api/health` | — | `{"ok": true, "llm_available": bool, "data_version": "2026-11-17"}` |
| `POST /api/goal/parse` | `{"text": str}` | `{"goal": Goal, "missing": ["days"], "actor": "llm"\|"rule"}` |
| `GET /api/config` | — | `{"interests": [{"key": "바다", "slot": false}], "regions": [{"region_id": str, "name": str}], "max_days": int, "supports": ["places", "picks"]}` (`config/interests.json`·`regions.json`·settings 값 그대로. `supports`는 선택 기능 목록 — 프론트는 있는 것만 켠다) |
| `GET /api/map` | — | `{"view_box": "0 0 W H", "emds": [{"emd": str, "region_id": str, "d": str}], "regions": [{"region_id": str, "name": str, "d": str}], "project": {"min_lon": f, "max_lat": f, "scale": f}}` |
| `GET /api/stats/emd?month=N` | month 생략 = 연평균 | `{"period": str, "source_id": "563", "items": [{"emd": str, "region_id": str, "visit_ratio": f\|null, "pct": f\|null}]}` |
| `POST /api/batch/a` | `{"goal": Goal, "inject_error": bool}` | `{"batch_id": str}` (실행은 백그라운드) |
| `POST /api/batch/b` | `{"prev_batch_id": str, "picks"?: [{"place_id": str, "day": int\|null}]}` (picks 최대 20) | `{"batch_id": str}`. picks = 직접 고른 장소: 꼭 갈래요처럼 고정. `day` 없으면 같은 권역의 날. 그날 고정 안 된 장소 중 같은 slot(음식·카페·일반)·최저 점수와 교체해 하루 장소 수를 지킨다. 고정 장소 때문에 생긴 권역 위반은 자동 수정하지 않고 `violations_remaining`으로 넘긴다 |
| `GET /api/places?batch_id=&region=&interest=&q=&sort=score\|quiet\|name&offset=0&limit=40` | 모두 선택. `batch_id`를 주면 그 실행의 Goal로 점수 계산. `limit` ≤ 200 | `{"total": int, "offset": int, "limit": int, "sort": str, "items": [Place]}` — 매 요청마다 DB를 읽으므로 데이터 갱신이 바로 반영 |
| `GET /api/batch/{id}/events?after=N` | `seq > N`인 이벤트만, 처음은 `after=0` | `{"events": [LogEvent], "done": bool, "result": BatchResult\|null, "error": str\|null}` |
| `POST /api/events` | `{"batch_id": str, "place_id": str, "type": "virtual_arrival"\|"feedback", "value": "interest"\|"must"\|"dislike"\|null}` | `{"ok": true}` |
| `GET /api/places/{id}/trend` | — | `{"place_id": str, "period": str\|null, "source_ids": ["189","190"], "series": [{"year_month": "2024-01", "domestic": int\|null, "foreign": int\|null}]}` |
| `GET /api/print/{batch_id}` | — | `text/html` 인쇄용 문서 |
| (선택) `GET /api/stats/emd?month=all` | — | `{"period": str, "source_id": "563", "months": {"1": [items], …, "12": [items]}}` — 없으면 프론트가 `month=1..12`로 12회 호출 |
| `GET /` 및 그 밖의 경로 | — | `web/dist` 아래 **모든 파일**(`/assets/*`, `/fonts/*` 등). 없는 경로는 `index.html` |

- 오류: `4xx/5xx` + `{"error": "사람이 읽을 메시지"}`. 잘못된 JSON·필수 키 누락은 400, 없는 batch id는 404. `error`는 화면에 그대로 보여줄 한국어 문장이다(예: "여행 기간이 없습니다").
- 정적 파일 `Content-Type`은 `mimetypes`에 맡기지 않고 고정 표로 준다: `.html` `text/html; charset=utf-8`, `.js` `text/javascript`, `.css` `text/css`, `.json` `application/json`, `.svg` `image/svg+xml`, `.woff2` `font/woff2`, `.png` `image/png`. (Windows Python은 레지스트리 값을 읽어 `.js`를 `text/plain`으로 줄 수 있고, 그러면 브라우저가 스크립트를 거부해 빈 화면이 된다.)
- 권역은 **4개로 확정**(912 원본의 권역 구분): `city` 제주시내권, `west` 서부권, `east` 동부권, `south` 중문·서귀포권. 중산간 권역은 두지 않는다. `GET /api/map`의 `regions[]`와 `GET /api/config`의 `regions[]`는 이 4개다.
- 지도 경계 원자료: 통계청 SGIS 행정동 경계를 가공한 `vuski/admdongkor` `ver20261001`(CC BY 4.0, 원자료 공공누리 1유형). 화면 범례 또는 데이터 출처 표에 "SGIS 행정동 경계(가공: vuski/admdongkor)"를 표기한다.
- 폴링 주기: 프론트 500ms. `done: true`가 되면 멈춘다.
- 한 번에 하나의 키오스크 사용자를 가정한다(동시 배치는 허용하되 사용자 구분 없음).

## 변경 이력

- 2026-11-17 (B 제안, A 확인 완료 — PR #2):  emd 키 형식 통일, `GET /api/config` 추가, `places` 포함 범위, `seq`·`after` 의미, Violation value/limit, 정적 파일 범위·MIME 고정, 중산간 권역 경로, 404·오류 문구, (선택) 월별 통계 일괄 조회. 근거: `2026-11-17-frontend-requirements.md` 4장
- 2026-11-17 (A): 중산간 권역 경로(C7) 삭제 — 912 원본 권역 4개로 확정. 지도 경계 출처 명시.
- 2026-11-18 (B, 키오스크 피드백 "추천 말고 내가 고르고 싶다"): `GET /api/places` 목록 추가, `POST /api/batch/b`에 선택 `picks` 추가, `GET /api/config`에 `supports`. 기존 요청·응답은 그대로(하위 호환). 구현·테스트: `tests/test_picks.py`
