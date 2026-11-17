# malttara-jeju (말따라 제주)

제주 AI·빅데이터 활용 AI Agent 개발 챌린지 출품 프로젝트.
진행 순서: **기획 다듬기 → 설계(구현 계획) → 구현 → 배포(최종 제출)** · 제출 마감 2026-11-20(금) 10:00

현재 단계: **구현** (설계 승인 11/16). 2인 팀이 트랙을 나눠 비공개 저장소에서 작업한다. 협업 규칙은 `CLAUDE.md`의 "팀 협업" 절.

| 트랙 | 계획서 | 담당 폴더 |
|---|---|---|
| A 데이터·에이전트 | `docs/superpowers/plans/2026-11-16-track-a-data-agent.md` | `src/` `config/` `data/` `tests/` `run.*` |
| B 프론트·UI | `docs/superpowers/plans/2026-11-16-track-b-frontend.md` | `web/` |
| 공용 계약 | `docs/superpowers/plans/2026-11-16-api-contract.md` | 바꿀 때 상대 확인 |

## 시작하기 (팀원 공통)

준비물: Git, Python 3.11 이상(python.org 설치본), Claude Code. (Node 불필요 — 프론트는 바닐라 JS)

```bash
git clone https://github.com/jomin4/malttara-jeju.git
cd malttara-jeju
cp .env.example .env      # 실제 키는 .env에만. 키는 비공개 메신저로 받는다
claude
```

Claude Code 안에서 superpowers 설치(둘 중 하나) 후 `/reload-plugins` 또는 재시작:

```
/plugin install superpowers@claude-plugins-official
```
```
/plugin marketplace add obra/superpowers-marketplace
/plugin install superpowers@superpowers-marketplace
```

### B 트랙(프론트) 첫 실행

```bash
cd web && python -m http.server 8799   # 서버·DB 없이 목업: http://127.0.0.1:8799/?mock=1
```
실서버와 붙일 때는 루트에서 `python web/build.py`(web/ → web/dist 복사) 후 `python run.py --mock` → http://127.0.0.1:8765/ . 파일을 고치면 build.py를 다시 실행한다. 상세 `web/README.md`. 실제 DB는 GitHub Release 첨부 파일(`malttara.sqlite`, `map.json`)을 받아 `data/db/`에 둔다.

### A 트랙(데이터·에이전트) 첫 실행

```bash
PYTHONPATH=src python -m unittest discover -s tests -v
```
원본 데이터는 허브에서 받아 `data/raw/`에(커밋 금지), 빌드는 `PYTHONPATH=src python -m malttara.etl.build_db`.

### 작업 흐름

```bash
git pull origin main
git switch -c b/task-03-step1          # 계획서 태스크 단위 브랜치 (a/… 또는 b/…)
# … 작업·커밋 …
git push -u origin b/task-03-step1
gh pr create --fill                     # squash merge. 계약 문서 변경 PR만 상대 리뷰 필수
```

### Claude Code 첫 요청 예시

> CLAUDE.md와 B 트랙 계획서(docs/superpowers/plans/2026-11-16-track-b-frontend.md), API 계약 문서를 읽고 executing-plans로 Task 1부터 진행하자. 태스크마다 브랜치를 만들고 PR로 올려줘.

> CLAUDE.md와 A 트랙 계획서를 읽고 executing-plans로 Task 1부터 진행하자.

## 폴더

| 경로 | 내용 |
|---|---|
| `CLAUDE.md` | Claude가 매 세션 읽는 규칙 (현재 단계, 핵심 원칙, 대회 제약) |
| `docs/01_planning/` | 기획 초안 v0, 결정 기록, 미결 사항, 데이터 선정 작업장, 검토 체크리스트 |
| `design/ui-prototype/` | UI 프로토타입과 기획 대응표 |
| `data/` | 제주데이터허브 1,259건 카탈로그·데이터 카드, 원본·DB 자리 |
| `docs/00_contest/` | 대회 공고·규칙·평가기준 요약 |
| `docs/superpowers/` | 설계 문서(specs)·구현 계획(plans) |
| `docs/02_proposal/`, `docs/05_submission/` | 제출용 기획서, 제출 체크리스트 |
| `src/`, `tests/` | 구현 |
| `submission/` | 최종 ZIP (git 제외) |

## UI 프로토타입 보기

`design/ui-prototype/code.html`을 브라우저로 연다. Tailwind·글꼴·이미지를 인터넷에서 불러오므로 오프라인에서는 화면이 깨진다(대응은 `design/ui-prototype/README.md`).
