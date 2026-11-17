# 말따라 제주 B 트랙(프론트·UI) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

> **2026-11-17 변경 (decisions.md B 항목):** 구현은 React+Vite+TS가 아니라 **바닐라 JS(ES 모듈)+SVG**로 했다. 번들러·Node·Tailwind 없음, `python web/build.py`가 `web/dist`로 복사. 아래 Task의 화면·문구·Review Focus·Global Constraints(수치는 서버 값, 미반영, 지표 분리, 외부 자원 금지 등)는 그대로 유효하고, 파일 구조·명령(`npm`, `tsc`, `VITE_MOCK`)은 `web/README.md`의 구조·명령으로 읽는다. 키오스크 점검으로 바뀐 화면 구성(근거 접기, 한국어 로그, 시연 토글 `?demo=1`, 자동 초기화)도 `web/README.md`에 있다.

**Goal:** 4개 화면(01 여행 설명+조건 확인, 02 경로 만들기, 03 미리보기 게임/목록, 04 다시 짜기+최종 계획)을 React로 만들어 정적 파일로 빌드하고, A 트랙 서버가 서빙하게 한다.

**Architecture:** Vite + React + TypeScript 단일 페이지 앱(`web/`). 화면 상태는 `useReducer` 하나에 모으고, 서버 호출은 `web/src/api/`가 계약 API를 감싼다(`VITE_MOCK=1`이면 픽스처). 지도·말·차트는 모두 SVG 컴포넌트. `npm run build` 결과 `web/dist/`를 Python 서버가 서빙한다(실행 시 Node 불필요).

**Tech Stack:** Node 24(개발 PC만), Vite, React 18, TypeScript, Tailwind CSS(빌드 시 설치, CDN 금지), Pretendard 글꼴(OFL, 로컬 동봉). 차트 라이브러리 없이 SVG 직접 작성.

**Spec:** `docs/superpowers/specs/2026-11-16-malttara-jeju-design.md` 7장 · **계약:** `docs/superpowers/plans/2026-11-16-api-contract.md` · **디자인 토큰:** `design/ui-prototype/DESIGN.md`

## Global Constraints

- 서비스명은 **"말따라 제주"**. "제주여정 AI", "Jeju Journey AI", "AGENTIC" 배지 문구를 쓰지 않는다.
- 화면에 나오는 수치는 모두 서버 응답 값이다. 프론트에서 거리·점수·비율을 계산하거나 예시 숫자를 하드코딩하지 않는다(소수 반올림 표시만). 만족도·평점·예상 이동시간 UI 없음.
- 거리 표기는 정확히 `직선 {total_km} km (도로거리·이동시간 아님)`.
- 입력하지 않은 조건은 `(미반영)` 칩. pace가 null이면 `여유 (미반영·보통 기준 적용)`, 동행은 값 뒤에 `(점수 미반영)`.
- 장소 지표는 두 블록으로 나눠 제목을 정확히: `{emd} 지표 (읍면동 단위)` / `장소 반경 {radius_km}km 지표`. 각 블록에 출처 ID와 기간(`563 · 2018-01~2022-09`)을 쓴다. `missing: true`면 `지표 없음`(0으로 표시하지 않음). "한적한 장소" 같은 장소 평가 문구 금지.
- 외부 네트워크 자원 금지: CDN 스크립트, Google Fonts, Material Symbols 웹폰트, 원격 이미지 URL. 아이콘은 `web/src/components/icons.tsx`의 인라인 SVG(직접 그린 단순 도형).
- 음성 입력 버튼, 사용자 프로필·아바타, "실시간 기상 API" 링크를 만들지 않는다.
- 화면 크기: 1920×1080 키오스크 기준, 1366×768에서도 가로 스크롤 없음. 물리 키보드 전제.
- 디자인 토큰은 DESIGN.md 값 그대로: primary `#005c55`, primary-container `#0f766e`, secondary `#9d4300`, secondary-container `#fd761a`, surface `#faf8ff`, on-surface `#131b2e`, outline-variant `#bdc9c6`, 모서리 sm 0.25rem / DEFAULT 0.5rem / md 0.75rem / lg 1rem / xl 1.5rem, 간격 gutter 1.5rem / margin 2rem. 글꼴은 Pretendard 하나(제목·본문 공통).
- 사용한 오픈소스·글꼴은 `docs/05_submission/README.md` 명시 사항 표에 이름·버전·라이선스로 기록.
- 커밋에 `web/node_modules`를 넣지 않는다. `web/dist`는 제출 ZIP에 넣는다(커밋 여부는 `.gitignore`에 `web/dist/` 추가 — 빌드 산출물).

## Review Focus

1. **한글 IME 조합 중 Enter/판정** — 03 게임에서 조합 중(`isComposing`)인 입력으로 정답 판정·제출하지 않는다. 조합이 끝난 값으로만 비교(Task 5 확인 항목).
2. **서버 지연·실패** — 배치 폴링이 20초 넘게 `done`이 아니거나 `error`가 오면 로그 아래에 오류 문구와 [다시 시도] 버튼. 화면이 멈추거나 빈 화면이 되지 않는다(Task 4).
3. **기간 미입력** — `missing`에 `days`가 있으면 [경로 만들기] 비활성, 기간 칩을 경고색으로 강조하고 입력 방법 안내(Task 3).
4. **지표 없음·분류 없음·입장객 통계 없음** — 각각 `지표 없음` / `분류 없음` / `해당 장소의 입장객 통계 없음`으로 표시(Task 4, 6).
5. **[처음부터]를 배치 진행 중에 누름** — 폴링을 멈추고 모든 상태를 초기화, 이전 배치 응답이 늦게 도착해도 화면에 반영하지 않는다(Task 1 reducer의 `session_id` 비교).

---

## 파일 구조

```
web/package.json, web/vite.config.ts, web/tsconfig.json, web/tailwind.config.ts, web/postcss.config.js, web/index.html
web/public/fonts/Pretendard-*.woff2, web/public/fonts/LICENSE-Pretendard.txt
web/src/main.tsx, web/src/App.tsx              앱 셸: 헤더, 단계 탭, [처음부터]
web/src/state.ts                               reducer, 액션, 초기 상태
web/src/api/types.ts                           계약 타입
web/src/api/client.ts                          fetch 래퍼, pollBatch()
web/src/api/mock.ts, web/src/api/fixtures/*.json  VITE_MOCK=1 픽스처
web/src/components/icons.tsx, Chip.tsx, PlaceCard.tsx, IndicatorBlock.tsx, LogStream.tsx, SvgMap.tsx, LineChart.tsx, Horse.tsx
web/src/screens/Step1Intent.tsx, Step2Plan.tsx, Step3Preview.tsx, Step4Replan.tsx
web/src/lib/format.ts                          거리·기간·미반영 문구, 타이핑 비교 normalize
```

---

### Task 1: 프론트 골격 · 토큰 · 글꼴 · API 계층 · 앱 셸

**Files:**
- Create: 위 구조 중 `web/package.json` ~ `web/src/state.ts`, `web/src/api/*`, `web/src/lib/format.ts`, `web/src/components/icons.tsx`
- Modify: `.gitignore`(`web/node_modules/`, `web/dist/`), `docs/05_submission/README.md`(Vite·React·TypeScript·Tailwind·Pretendard 버전·라이선스)

**Interfaces:**
- Consumes: 계약 1·2장
- Produces:
  - `types.ts`: `Goal`, `Place`, `Indicators`, `Itinerary`, `Route`, `Violation`, `LogEvent`, `BatchResult`, `DiffItem`, `MapData`, `EmdStats`, `Trend` — 계약 필드명 그대로(snake_case).
  - `client.ts`: `parseGoal(text: string): Promise<{goal: Goal; missing: string[]; actor: string}>`, `getMap(): Promise<MapData>`, `getEmdStats(month: number | null): Promise<EmdStats>`, `startBatchA(goal: Goal, injectError: boolean): Promise<string>`, `startBatchB(prevBatchId: string): Promise<string>`, `pollBatch(id: string, onEvents: (e: LogEvent[]) => void, signal: AbortSignal, onSlow: () => void): Promise<BatchResult>`(500ms 간격, 20초가 지나면 `onSlow()`를 한 번 부르고 계속 폴링, `error`면 reject, `signal` 중단 시 reject), `postEvent(e: {batch_id; place_id; type; value}): Promise<void>`, `getTrend(placeId: string): Promise<Trend>`, `printUrl(batchId: string): string`. `import.meta.env.VITE_MOCK === "1"`이면 `mock.ts` 구현으로 교체.
  - `state.ts`: `type Step = 1 | 2 | 3 | 4`, `State = {session_id: number; step; text; goal: Goal | null; missing: string[]; batchA: {id; events; result; error} | null; batchB: …; feedback: Record<string, "interest" | "must" | "dislike">; previewMode: "game" | "list"; injectError: boolean}`, 액션 `RESET`(session_id 증가), `SET_TEXT`, `GOAL_PARSED`, `EDIT_GOAL`, `BATCH_STARTED`, `BATCH_EVENTS`, `BATCH_DONE`, `BATCH_ERROR`, `SET_FEEDBACK`, `SET_MODE`, `GO_STEP`. 배치 관련 액션은 `session_id`가 다르면 무시.
  - `format.ts`: `distanceLabel(km: number): string` → `직선 ${km.toFixed(1)} km (도로거리·이동시간 아님)`, `unsetLabel(field: string): string`, `normalizeTyping(s: string): string`(공백 제거, NFC).
  - `App.tsx`: 헤더 왼쪽 "말따라 제주", 가운데 단계 탭 4개(`01 여행 설명` `02 경로 만들기` `03 미리보기` `04 다시 짜기`, 아직 못 가는 단계는 비활성), 오른쪽 [처음부터]. 탭 아래 현재 화면.
  - `vite.config.ts`: dev 서버 `/api` → `http://127.0.0.1:8765` 프록시, `base: "/"`.

- [ ] **Step 1: 생성** — `npm create vite@latest web -- --template react-ts` 후 Tailwind 설치·설정, 버전은 `package.json`에 정확히 고정(`^` 제거). Pretendard woff2(Regular·Medium·SemiBold·Bold)와 라이선스 파일을 공식 배포본에서 받아 `web/public/fonts/`에 두고 `@font-face`로 연결.
- [ ] **Step 2: 타입·클라이언트·목업·reducer·셸 작성** — 픽스처는 계약 예시를 바탕으로 모의 장소 이름(`모의 해변 1` 등)만 쓴다(실제 장소명·수치를 지어내지 않는다).
- [ ] **Step 3: 타입 검사·빌드** — Run: `cd web && npx tsc --noEmit && npm run build` → Expected: 오류 0, `web/dist/index.html` 생성
- [ ] **Step 4: 외부 자원 점검** — Run: `grep -rnE "https?://" web/dist | grep -v "127.0.0.1"` → Expected: 출력 없음
- [ ] **Step 5: 화면 확인** — Run: `cd web && VITE_MOCK=1 npm run dev` → 브라우저에서 헤더·탭·[처음부터]가 보이고 콘솔 오류 없음
- [ ] **Step 6: Commit** — `git add web .gitignore docs/05_submission/README.md && git commit -m "feat(b): 프론트 골격, 토큰, 글꼴, API 계층, 앱 셸"`

---

### Task 2: SVG 지도 컴포넌트

**Files:**
- Create: `web/src/components/SvgMap.tsx`, `web/src/components/Horse.tsx`

**Interfaces:**
- Consumes: `MapData`, `EmdStats`, `Place`, `Itinerary`
- Produces:
  - `project(lat: number, lon: number, p: MapData["project"]): [number, number]` — A 트랙 `build_map`과 같은 식: `x = (lon - min_lon) * scale * cos(33.4°)`, `y = (max_lat - lat) * scale`.
  - `<SvgMap map={MapData} emdValues?={Record<string, number | null>} legend?={{title: string; source: string; period: string}} itinerary?={Itinerary} places?={Record<string, Place>} activeDay?={number} horseAt?={[number, number] | null} highlightRegion?={string} onPlaceClick?={(id) => void} />`
    - 읍면동 path 채우기: `emdValues`(0~1 백분위) → primary 계열 5단계, null은 빗금 패턴 + 범례 "지표 없음".
    - 권역 외곽선 굵은 선 + 권역 이름 라벨(권역 path 중심).
    - 일정: 날짜별 색(primary, secondary, 청록 밝은색 …) 직선 연결선 + 순번 원 마커. 선 위에 거리 숫자를 그리지 않는다(거리는 목록에 서버 값으로).
    - `horseAt`이 있으면 `<Horse>`(단순 SVG 말 실루엣)를 그 좌표에 `transform` 전환(CSS transition 600ms)으로 이동.
  - 범례 문구: `{legend.title} · 출처 {legend.source} · {legend.period}`.

- [ ] **Step 1: 구현**
- [ ] **Step 2: 확인** — 목업 지도 픽스처로 01 화면 자리에 임시 렌더 → 읍면동 색, 권역 선, 지표 없음 빗금, 말 이동 전환이 보인다. 1366×768에서 지도 전체가 잘리지 않는다.
- [ ] **Step 3: 타입 검사** — `cd web && npx tsc --noEmit` → 오류 0
- [ ] **Step 4: Commit** — `git commit -m "feat(b): SVG 지도, 말 컴포넌트"`

---

### Task 3: 01 여행 설명 + 조건 확인

**Files:**
- Create: `web/src/screens/Step1Intent.tsx`, `web/src/components/Chip.tsx`

**Interfaces:**
- Consumes: `parseGoal`, `getMap`, `getEmdStats`, reducer, `SvgMap`
- Produces: 화면(설계 7장 01)
  - 제목 `나만의 제주 여행을 한 줄로 들려주세요`, 여러 줄 입력창(placeholder `예: 2박 3일 동안 바다를 보며 여유롭게 쉬고 싶어요`).
  - 예시 버튼 3개(누르면 입력창에 채움, 문장은 그대로):
    - `2박 3일 동안 바다를 보며 여유롭게 쉬고, 현지 음식도 먹고 싶어요`
    - `아이와 함께 1박 2일, 렌터카로 오름이랑 체험 위주로 다니고 싶어요`
    - `혼자 3박 4일, 버스로 조용한 동네와 카페를 천천히 보고 싶어요`
  - [조건 확인하기] → `parseGoal` → 조건 칩 줄: 기간·여유·관심·한적함·이동수단·동행·출발지·날짜. 값 없으면 `(미반영)`. 칩을 누르면 작은 편집 패널(기간: 숫자 선택 1~7일 / 여유: 3택+미반영 / 관심: 설정 키 다중 선택 / 이동수단: 3택+미반영 / 월: 1~12+미반영 / 동행·출발지: 텍스트+지우기) → `EDIT_GOAL`. 판단 주체 표시: `해석: AI` 또는 `해석: 규칙`.
  - `missing`에 `days`가 있으면 기간 칩 경고색 + `여행 기간(예: 2박 3일)을 입력하거나 기간 칩을 눌러 골라 주세요`, [경로 만들기] 비활성.
  - [경로 만들기] → `GO_STEP 2`(배치 시작은 02에서).
  - 하단 `데이터로 보는 제주`: `SvgMap`에 `getEmdStats(goal?.month ?? null)`의 pct를 칠함, 범례 `읍면동별 방문/거주 비율 · 출처 563 · {period}` + 한 줄 설명 `읍면동 단위 통계입니다. 개별 장소의 혼잡도가 아닙니다.`
- [ ] **Step 1: 구현**
- [ ] **Step 2: 확인(목업)** — 예시 1 → 칩 `기간 2박 3일`, `여유 여유롭게`, `관심 바다·음식`, 나머지 `(미반영)`. "바다 보고 싶어요" → 버튼 비활성 + 안내. 기간 칩에서 3일 고르면 버튼 활성.
- [ ] **Step 3: 타입 검사** — `cd web && npx tsc --noEmit` → 오류 0
- [ ] **Step 4: Commit** — `git commit -m "feat(b): 01 여행 설명·조건 확인 화면"`

---

### Task 4: 02 경로 만들기 (Batch A)

**Files:**
- Create: `web/src/screens/Step2Plan.tsx`, `web/src/components/LogStream.tsx`, `web/src/components/PlaceCard.tsx`, `web/src/components/IndicatorBlock.tsx`

**Interfaces:**
- Consumes: `startBatchA`, `pollBatch`, `BatchResult`, `SvgMap`, `distanceLabel`
- Produces:
  - 화면 진입 시 `startBatchA(goal, injectError)` 한 번(같은 session에서 결과가 있으면 다시 시작하지 않음). 상단 토글 `오류 주입 시연`(켜면 [다시 만들기]로 재실행).
  - 왼쪽 `<LogStream events={LogEvent[]} batchId />`: 제목 `실행 로그 {batch_id}`, 줄마다 상태 기호(ok ✓, fail ✗, fix ↻, add ＋, skip −), tool 이름, 판단 주체 배지(`AI`/`규칙`/`코드`), message. 새 줄이 오면 아래로 자동 스크롤. 20초 넘게 진행 중이면 `시간이 걸리고 있습니다…`, `error`면 오류 문구 + [다시 시도].
  - 오른쪽: `SvgMap`(일정 선·마커, 날짜 탭으로 `activeDay`), 그 아래 날짜별 목록: `{day}일차 · {region_name}` + `distanceLabel(route.total_km)`, 장소 순서대로 `PlaceCard`.
  - `<PlaceCard place alternatives? explanations? compact? actions? />`: 이름, 분류(`category ?? "분류 없음"`, `category_source` 작은 글씨), 개요(있으면 3줄 말줄임), `<IndicatorBlock>` 2개, 근거 문장 목록(서버 explanations 그대로), 대안 장소 이름(있으면).
  - `<IndicatorBlock kind="region" | "nearby" data />`: 제목은 Global Constraints 문구, 값 줄: region은 `방문/거주 비율 {visit_ratio.toFixed(2)} · 범위 내 백분위 {Math.round(pct*100)}`, nearby는 `렌터카 체류 {quiet_count}건 · 범위 내 백분위 {Math.round(pct*100)}`, 출처 줄 `{source_id} · {period}`. missing이면 `지표 없음`.
  - `violations_remaining`이 있으면 목록 위에 경고 상자: 위반 종류별 한국어 문구(`distance`→`{day}일차 직선 합계 {value} km가 기준 {limit} km를 넘습니다`, `regions`→`{day}일차에 권역 {value}곳 방문(기준 {limit})`, `count`→`{day}일차 장소 {value}곳(목표 {limit}곳) — 조건에 맞는 장소가 부족합니다`, 나머지도 같은 형식).
  - 요약 문단(`summary`)과 품질(`quality`: `분류 없음 n곳 · 읍면동 지표 없음 n곳 · 반경 지표 없음 n곳`).
  - [미리보기로] → `GO_STEP 3`.
- [ ] **Step 1: 구현**
- [ ] **Step 2: 확인(목업 또는 `python run.py --mock` + `npm run dev`)** — 로그가 순서대로 늘어나고, 오류 주입을 켜면 ✗ 다음 ↻ 줄이 보인다. 장소 카드에 두 지표 블록이 다른 제목으로 따로 보인다. 서버를 끈 상태에서 오류 문구·[다시 시도]가 보인다.
- [ ] **Step 3: 타입 검사** — `cd web && npx tsc --noEmit` → 오류 0
- [ ] **Step 4: Commit** — `git commit -m "feat(b): 02 경로 만들기 화면, 로그, 장소 카드"`

---

### Task 5: 03 미리보기 — 게임 모드 · 목록 모드

**Files:**
- Create: `web/src/screens/Step3Preview.tsx`

**Interfaces:**
- Consumes: `BatchResult.quests`, `places`, `postEvent`, `normalizeTyping`, `SvgMap`, `PlaceCard`
- Produces:
  - 상단 전환 `[게임 | 목록]`(`SET_MODE`), 안내 `게임은 선택입니다. 목록에서도 같은 버튼을 쓸 수 있어요.`
  - 게임: 날짜 탭 → 그 날 `quests.items` 순서. 지도에 말(`horseAt`), 화면 아래 큰 글씨 `다음 목적지: {label}`, 입력창(자동 포커스). 판정: `compositionend` 이후 또는 Enter(`!e.nativeEvent.isComposing`)일 때 `normalizeTyping(입력) === normalizeTyping(label)`이면 도착 → 말 이동, `postEvent({type: "virtual_arrival", value: null})`, 도착 카드(`PlaceCard compact` + 버튼 3개). 틀리면 입력창 흔들림 + 정답 글자 수 힌트만(자동 정답 공개 없음), [건너뛰기] 버튼 제공.
  - 반응 버튼 `관심` `꼭 갈래요` `별로예요` → `postEvent({type: "feedback", value: "interest"|"must"|"dislike"})` + `SET_FEEDBACK`(다시 누르면 같은 값 유지, 다른 값 누르면 바뀜 — 서버는 마지막 값 사용).
  - 목록: 날짜별 `PlaceCard` + 같은 버튼 3개(가상 도착 이벤트는 보내지 않음).
  - 하단 [다시 짜기] → `GO_STEP 4`(반응 0개여도 가능).
- [ ] **Step 1: 구현**
- [ ] **Step 2: 확인** — 한글 IME로 라벨 입력: 조합 중 Enter가 오판정되지 않는다. 정답이면 말이 다음 마커로 이동하고 카드가 뜬다. 목록 모드에서 누른 반응이 게임 모드로 전환해도 유지된다. 네트워크 탭에서 `virtual_arrival`·`feedback` 요청이 따로 간다.
- [ ] **Step 3: 타입 검사** — `cd web && npx tsc --noEmit` → 오류 0
- [ ] **Step 4: Commit** — `git commit -m "feat(b): 03 미리보기 게임·목록 모드"`

---

### Task 6: 04 다시 짜기 + 최종 계획 · 차트 · 인쇄

**Files:**
- Create: `web/src/screens/Step4Replan.tsx`, `web/src/components/LineChart.tsx`

**Interfaces:**
- Consumes: `startBatchB`, `pollBatch`, `getEmdStats`, `getTrend`, `printUrl`, `LogStream`, `PlaceCard`, `SvgMap`
- Produces:
  - 진입 시 `startBatchB(batchA.id)` 한 번. `LogStream`(제목 `실행 로그 {B id} (이전 {A id})`).
  - 변경 전후 비교: 날짜별 2열(이전 / 이후), `DiffItem.change`별 배지 색과 문구 `유지` `고정` `교체` `추가` `제외`, 교체는 `이전 → 이후` 화살표, 이유(`reason`) 표시.
  - 최종 일정: 02와 같은 지도·날짜 목록·`PlaceCard`(근거 패널 포함: 데이터 ID·기간·대안 장소).
  - `<LineChart series={{x: string; y: number | null}[][]} labels unit source period />`: 축·눈금·범례를 SVG로 직접. null 구간은 끊어 그림.
    - 차트 1: 일정 장소가 있는 읍면동들의 월별 visit_ratio — 월 1~12마다 `getEmdStats(m)`(12회, 캐시) 결과에서 해당 읍면동 값. 제목 `일정 지역의 월별 방문/거주 비율 (읍면동 단위)`, 출처 `563 · {period}`.
    - 차트 2: `has_trend`인 일정 장소별 `getTrend` 내국인·외국인 입장객. 제목 `관광지 입장객 추이`, 출처 `189·190 · {period}`. 해당 장소가 없으면 `해당 장소의 입장객 통계 없음`.
  - [인쇄] → `window.open(printUrl(batchB.id))`(서버가 만든 인쇄용 HTML). [처음부터]는 헤더에 있음.
- [ ] **Step 1: 구현**
- [ ] **Step 2: 확인** — 03에서 꼭 갈래요 1·별로예요 1을 누르고 오면 `고정`·`교체` 배지가 보인다. 반응 없이 오면 전부 `유지`. 차트 2개가 출처·기간과 함께 그려지고, 통계 없는 경우 문구가 나온다. 인쇄 창이 열린다.
- [ ] **Step 3: 타입 검사** — `cd web && npx tsc --noEmit` → 오류 0
- [ ] **Step 4: Commit** — `git commit -m "feat(b): 04 다시 짜기·최종 계획, 차트, 인쇄"`

---

### Task 7: 실서버 통합 · 빌드 동봉 · 오프라인 점검 · 매뉴얼

A 트랙 Task 14(서버)가 끝난 뒤 진행한다.

**Files:**
- Modify: `web/src/api/client.ts`(목업 경로 정리), `docs/05_submission/manual_run.md`(A 초안에 화면 사용법 추가), `docs/05_submission/README.md`(명시 사항 최종), `README.md`(실행 요약)

**Interfaces:**
- Consumes: A 트랙 `run.py`, 계약 2장

- [ ] **Step 1: 빌드** — Run: `cd web && npm run build` → Expected: `web/dist/` 생성
- [ ] **Step 2: 실데이터 완주** — Run: `PYTHONPATH=src python run.py` (실제 DB) → 브라우저 `http://127.0.0.1:8765/`에서 테스트 프로필 3종으로 01→04 완주. 프로필 3에서 한적함 반영 로그(`get_region_data` 추가)가 보이는지, 프로필 1에서 음식점이 하루 1곳씩 들어가는지 확인.
- [ ] **Step 3: LLM 없이 완주** — `.env`의 `LLM_API_KEY`를 비우고 재시작 → 로그의 판단 주체가 전부 `규칙`/`코드`, 흐름 완주.
- [ ] **Step 4: 오프라인 자원 점검** — 브라우저 개발자 도구 네트워크 탭에서 `127.0.0.1` 외 요청 0건(LLM 호출은 서버 쪽이라 브라우저에 안 보임). `grep -rnE "https?://" web/dist | grep -v 127.0.0.1` → 출력 없음.
- [ ] **Step 5: 원칙 점검** — `docs/01_planning/review-checklist.md` 3장 항목을 화면 기준으로 체크(만족도·평점 없음, 미반영 칩, 지표 분리, 직선거리 문구, 데이터에 없는 장소명 없음).
- [ ] **Step 6: 매뉴얼** — `manual_run.md`에 화면별 사용법과 스크린샷 자리, 게시판 답변이 요구한 항목(Python 버전, 패키지 없음, 설치 순서, 파일 경로, 최초 실행, 오류 시 조치: 포트 사용 중·DB 없음·브라우저 안 열림)을 비개발자 문장으로.
- [ ] **Step 7: Commit** — `git commit -m "feat(b): 실서버 통합, 빌드 동봉, 매뉴얼"`
