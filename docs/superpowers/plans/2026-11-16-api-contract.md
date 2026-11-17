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
  "emd": "애월읍", "region_id": "west", "region_name": "서부",
  "category": "해수욕장", "category_source": "tourapi",   // tourapi|hub_811|hub_812|hub_784|hub_858|keyword|none
  "overview": "…" ,                                         // TourAPI 개요, 없으면 null
  "source": "1349",                                          // "1349" | "tourapi"
  "score": 0.82, "interest": 1.0, "spread": 0.7, "quiet": 0.5,
  "indicators": {
    "region": {"emd": "애월읍", "visit_ratio": 3.21, "pct": 0.3, "period": "2018-01~2022-09", "month": null, "source_id": "563", "missing": false},
    "nearby": {"quiet_count": 412, "pct": 0.5, "radius_km": 1.0, "period": "2021-07~12 토요일", "source_id": "1208", "missing": false}
  },
  "has_trend": true
}
```
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

### LogEvent (실행 로그 한 줄)
```json
{"seq": 3, "batch_id": "A-1116-193916", "tool": "validate_itinerary",
 "actor": "code", "status": "fail", "message": "2일차 직선 71.3km > 60km", "ts": "2026-11-16T19:39:18"}
```
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
| `GET /api/map` | — | `{"view_box": "0 0 W H", "emds": [{"emd": str, "region_id": str, "d": str}], "regions": [{"region_id": str, "name": str, "d": str}], "project": {"min_lon": f, "max_lat": f, "scale": f}}` |
| `GET /api/stats/emd?month=N` | month 생략 = 연평균 | `{"period": str, "source_id": "563", "items": [{"emd": str, "region_id": str, "visit_ratio": f\|null, "pct": f\|null}]}` |
| `POST /api/batch/a` | `{"goal": Goal, "inject_error": bool}` | `{"batch_id": str}` (실행은 백그라운드) |
| `POST /api/batch/b` | `{"prev_batch_id": str}` | `{"batch_id": str}` |
| `GET /api/batch/{id}/events?after=N` | — | `{"events": [LogEvent], "done": bool, "result": BatchResult\|null, "error": str\|null}` |
| `POST /api/events` | `{"batch_id": str, "place_id": str, "type": "virtual_arrival"\|"feedback", "value": "interest"\|"must"\|"dislike"\|null}` | `{"ok": true}` |
| `GET /api/places/{id}/trend` | — | `{"place_id": str, "period": str\|null, "source_ids": ["189","190"], "series": [{"year_month": "2024-01", "domestic": int\|null, "foreign": int\|null}]}` |
| `GET /api/print/{batch_id}` | — | `text/html` 인쇄용 문서 |
| `GET /`, `/assets/*` | — | `web/dist` 정적 파일 (없는 경로는 `index.html`) |

- 오류: `4xx/5xx` + `{"error": "사람이 읽을 메시지"}`. 잘못된 JSON·필수 키 누락은 400.
- 폴링 주기: 프론트 500ms. `done: true`가 되면 멈춘다.
- 한 번에 하나의 키오스크 사용자를 가정한다(동시 배치는 허용하되 사용자 구분 없음).
