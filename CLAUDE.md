# CLAUDE.md

이 저장소는 **제주 AI·빅데이터 활용 AI Agent 개발 챌린지** 출품작 **「말따라 제주」**를 만드는 프로젝트다.
문서와 대화는 한국어로 한다.

## 목표와 마감

- 여행자의 한 줄 요청을 해석해 제주 여행 경로를 만들고, 스스로 검증·수정하며, 말 타이핑 게임(또는 목록)으로 미리 둘러본 반응을 반영해 경로를 다시 짜는 AI Agent. 운영 형태는 제주빅데이터센터 체험형 키오스크.
- **최종 제출 마감: 2026-11-20(금) 10:00 (KST)**. 08:00까지 제출을 끝낸다.
- 대회 원문 요약: `docs/00_contest/` (규칙·평가기준 판단 근거)

## 진행 단계

```
기획 다듬기 → 설계(구현 계획) → 구현 → 배포(최종 제출)
```

**현재 단계: 구현** — 설계 `docs/superpowers/specs/2026-11-16-malttara-jeju-design.md`(11/16 승인), 계획 `docs/superpowers/plans/2026-11-16-*.md`  ← 단계가 바뀌면 이 줄을 갱신한다.

주제와 기본 기획은 이미 정해졌다. 출발점은 **완성본이 아닌 초안**이다.
- 기획 초안: `docs/01_planning/기획문서_v0.md` (원본, 수정하지 않는다)
- UI 프로토타입: `design/ui-prototype/` (STAGE 01 화면 1개뿐. 먼저 `design/ui-prototype/README.md`를 읽는다)

| 단계 | superpowers 스킬 | 산출물 | 시간 상한 |
|---|---|---|---|
| 기획 다듬기 (D3·D4 결정 포함) | brainstorming — 기획문서_v0 + UI + data/ 카드를 읽고 빈틈·불일치를 한 번에 하나씩 질문 | `docs/superpowers/specs/YYYY-MM-DD-malttara-jeju-design.md`, `docs/01_planning/*` 갱신 | **11/16(월) 밤** |
| 설계 → 구현 계획 | writing-plans — A(데이터·에이전트) / B(프론트·UI) 두 트랙으로 나눔 | `docs/superpowers/plans/` | **11/17(화) 오전** |
| 구현 | subagent-driven-development 또는 executing-plans, test-driven-development, systematic-debugging | `src/`, `tests/` | 11/17 ~ **11/18(수) 밤 기능 동결** |
| 검증·제출 | verification-before-completion, finishing-a-development-branch | `docs/02_proposal/`, `docs/05_submission/`, `submission/` | **11/19(목) 밤 1차 제출**, 11/20 08:00 최종 |

진행 규칙:
- 단계를 넘기 전에 산출물을 사용자에게 보여주고 **승인을 받는다**.
- 기획을 바꾸면 `docs/01_planning/decisions.md`에 변경 이력을 남긴다. 기획문서_v0는 덮어쓰지 않는다.
- 시간이 부족하다. 기획 다듬기는 **D3·D4 결정과 기획-UI 불일치 해소**를 우선하고, 이미 확정된 결정(D1·D2·D5~D8)은 사용자가 원할 때만 다시 연다.
- TDD는 핵심 로직(데이터 조회, Tool, 일정 검증)에만. UI는 생략. git worktree는 쓰지 않는다.
- superpowers 문서 경로는 기본값을 그대로 쓴다.

## 기획의 핵심 원칙 (기획문서_v0 1.3, 설계·구현 내내 지킨다)

1. 수치는 언제나 Tool(코드) 결과에서만 나온다. LLM은 수치를 만들지 않는다.
2. 사용자가 입력하지 않은 조건은 임의로 채우지 않고 "미반영"으로 둔다.
3. 지역 단위 통계를 개별 장소의 속성으로 표시하지 않는다.
4. 게임과 AI 기능은 강제하지 않는다. 목록 화면에서도 같은 기능을 쓸 수 있다.
5. 게임 속 가상 탐험과 실제 방문 기록은 따로 저장한다.
6. 도로망 데이터 없이는 직선거리를 이동 시간으로 표현하지 않는다.
7. AI는 계획을 보조하고, 최종 선택은 사용자가 한다.

UI 프로토타입에는 이 원칙과 어긋나는 요소(하드코딩된 km·만족도, 임의로 채운 날짜·출발지 등)가 있다. 목록은 `design/ui-prototype/README.md` 참고. 프로토타입은 **화면 구성과 디자인 톤의 참고자료**이지 사양이 아니다.

## 결정 현황

- 확정: D1 키오스크 · D2 2인/11월 19일 밤 작동 · D5 Solar Pro 4 + 규칙 폴백 · D6 React+SVG(Phaser 미사용) · D7 API 모드 + 규칙 기반 폴백 · D8 11/18 기능 동결
- 확정(11/16): D3 필수 데이터 · D4 본섬 전역·5권역 · D9~D16 · **D17 실행 중 서버는 Python 표준 라이브러리만** · D18 가공 DB 동봉 → `docs/01_planning/decisions.md`

## 팀 협업 (2인, 공개 GitHub 저장소 jomin4/malttara-jeju)

- 트랙과 담당 폴더. 자기 트랙 폴더만 고친다.

| 트랙 | 계획서 | 담당 폴더 |
|---|---|---|
| A 데이터·에이전트 | `docs/superpowers/plans/2026-11-16-track-a-data-agent.md` | `src/` `config/` `data/` `tests/` `run.py` `run.bat` `requirements*.txt` |
| B 프론트·UI | `docs/superpowers/plans/2026-11-16-track-b-frontend.md` | `web/` |

- 두 트랙의 접점은 **`docs/superpowers/plans/2026-11-16-api-contract.md` 하나**다. 계약을 바꿔야 하면 계약 문서를 고치는 PR을 먼저 열고 상대 트랙의 확인을 받는다. 계약과 다른 응답·요청을 코드에서 먼저 만들지 않는다.
- 공용 문서 중 `docs/05_submission/README.md`(명시 사항 표)와 `docs/01_planning/decisions.md`(변경 이력)는 **줄 추가만** 한다. `CLAUDE.md`는 PR로만 바꾼다.
- 브랜치: `main`은 항상 실행되는 상태. 작업은 계획서 태스크 단위 브랜치(`a/task-07-scoring`, `b/task-03-step1`)에서 하고 PR → squash merge. 계약 변경 PR만 상대 리뷰 필수, 나머지는 본인이 merge 가능. 작업 시작 전 `git pull origin main`.
- 커밋 메시지 접두: `feat(a):` `feat(b):` `fix(a):` `docs:` `test(a):` (계획서 형식).
- 저장소에 올리지 않는 것: `.env`(키), `data/raw/`, `data/db/`, `submission/`, `node_modules/`, `dist/`. 키는 비공개 메신저로 주고받는다. 빌드된 DB(`malttara.sqlite`, `map.json`)는 GitHub Release 첨부 파일로 공유한다.
- B 트랙은 DB 없이 시작한다: 프론트 목업(`VITE_MOCK=1`) → A 트랙 Task 14 이후 `python run.py --mock`(모의 서버) → Release의 실제 DB.
- 전체: `docs/01_planning/decisions.md`, 미결·리스크: `docs/01_planning/open-questions.md`

## 대회 제약 (모든 단계에서 지킬 것)

- **필수 데이터**: 제주데이터허브 데이터 1종 이상을 실질적으로 활용. 방침은 **허브 데이터만 사용**(센터 데이터 미사용).
- **실행 환경**: 센터 PC 최소사양 Intel i7-8700 / GTX 1060 / RAM 32GB / **VRAM 3GB**. 외부 LLM API + 규칙 기반 폴백이 기본.
- **제출물 2종**: ① 기획서(15쪽 이내) ② 결과물 ZIP(실행 소스 코드, 실행환경·매뉴얼, 데이터 활용 명세, 결과 설명자료). 상세: `docs/00_contest/02_규칙_제출물.md`.
- **키 관리**: 데이터 API 키(허브 프로젝트키)는 제출물에 넣지 않고 발급 방법만 매뉴얼에. 외부 AI API 평가용 키만 예외(한도 설정, 평가 후 폐기). 코드에 하드코딩하지 않고 `.env`로만 읽는다.
- **명시 의무**: 사용 AI 모델, AI 활용 범위, 외부 API·서비스, 외부 데이터, 오픈소스·외부 코드(글꼴·아이콘 포함)를 `docs/05_submission/`에 누적 기록.
- **평가 배점**(전문가 70% + 상호평가 30%): 기술성·완성도 25 / 편의성·실용성 25 / 필수 데이터 활용 20 / 주제 타당성·창의성 15 / 신뢰성·재현성 15. 상호평가에는 **기획서만** 공개된다.
- 결과물 소유권은 제주빅데이터센터에 귀속. 개인정보·민감정보를 포함하지 않는다.

## 데이터

- 데이터 관련 작업은 **`data/README.md`부터 읽는다.** (제주데이터허브 공개 데이터 1,259건의 카탈로그와 데이터별 카드)
- 카드 대부분은 `status: meta-only`(메타데이터만 확인, 실제 원본 미확인)다. D3 후보는 샘플/원본을 받아 컬럼·기간·좌표를 **직접 확인한 뒤** 확정하고, 카드의 '분석 결과'와 `status`를 갱신한다.
- 수치는 카드의 '분석 결과' 또는 DB 조회 결과로만 말한다. `period_meta`를 실제 기간으로 단정하지 않는다.
- 원본 수집 방법: `data/guides/how-to-collect.md`

## 폴더 지도

```
CLAUDE.md                 이 파일
README.md                 사람용 시작 안내
data/                     허브 1,259건 카탈로그·카드·원본·DB (data/README.md)
design/ui-prototype/      UI 프로토타입(code.html, DESIGN.md, screens/) + 대응표 README
docs/00_contest/          대회 공고·규칙·평가기준·데이터 안내
docs/01_planning/         기획 초안(v0)·결정·미결·데이터 선정·검토 체크리스트
docs/superpowers/specs/   brainstorming 결과 설계 문서 (기획 다듬기의 최종 산출물)
docs/superpowers/plans/   writing-plans 구현 계획
docs/02_proposal/         대회 제출용 기획서(15쪽)
docs/05_submission/       제출 체크리스트·명시 사항 기록
src/  tests/              구현 코드와 테스트
submission/               최종 ZIP 빌드 결과 (git 제외)
```

## 금지

- `data/raw/`, `data/db/`, `.env`, `submission/`을 커밋하지 않는다.
- 대회 제공 데이터 목록 xlsx 등은 외부 배포·공개 저장소 업로드 금지. **저장소는 공개(11/17 전환)** 이므로 커밋 즉시 공개된다: 키는 `.env`에만, 실수로 커밋했으면 즉시 재발급.
- 대회 원문에 없는 규칙을 지어내지 않는다. 불확실하면 `docs/00_contest/`를 확인하고, 없으면 사용자에게 묻는다.
- 데이터로 확인하지 않은 장소·수치를 기획서나 화면 예시에 사실처럼 쓰지 않는다.
