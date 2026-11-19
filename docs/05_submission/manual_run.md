# 말따라 제주 — 실행환경·설치·실행 매뉴얼

- 대상: 개발 경험이 없는 평가자·센터 운영자. 순서대로 따라 하면 실행된다.
- 작성: 2026-11-19 (A 트랙). 근거: `run.bat`, `run.py`, `src/malttara/server/app.py`, `src/malttara/agent/llm.py`, `src/malttara/etl/build_db.py`, `.env.example`, `config/settings.json`
- 한 줄 요약: **Python 3.11 이상만 설치하고 `run.bat`을 더블클릭한다.** 추가 패키지 설치는 없다.

---

## 1. 실행 환경

| 항목 | 내용 |
|---|---|
| 운영체제 | Windows 10/11 64비트 (센터 PC: Windows 11, i7-8700, GTX 1060, RAM 32GB에서 실행하는 것을 전제로 만들었다) |
| Python | **3.11 이상** (python.org 공식 설치본 권장. 개발은 3.14, 코드는 3.11 문법만 사용) |
| 추가 Python 패키지 | **없음.** 실행 중 코드는 Python 표준 라이브러리만 쓴다(`requirements.txt`는 비어 있다). `pip install` 단계가 없다 |
| Node.js·빌드 도구 | 필요 없음. 화면(`web/dist`)은 이미 만들어진 파일로 동봉한다 |
| GPU·VRAM | 사용하지 않음. 로컬 AI 모델을 돌리지 않는다 |
| 브라우저 | Chrome 또는 Edge 최신판 (Windows 기본 브라우저가 자동으로 열린다) |
| 인터넷 | 없어도 전 기능이 돈다(규칙 기반 모드). 있고 AI 키가 있으면 외부 AI(Claude Haiku 5.5)를 쓴다 |
| 디스크 | 압축 해제 후 수십 MB 수준. 압축을 푼 폴더에 **쓰기 권한**이 있어야 한다(실행 기록을 DB에 저장) |
| 서명 없는 확장 모듈(.pyd/.dll) | 쓰지 않음. 외부 패키지를 설치하지 않으므로 센터 보안 정책의 확장 모듈 실행 제한에 걸리지 않는다 |

자동 검사: `tests/test_acceptance.py`의 `test_11_runtime_imports_stdlib_only`가 실행 중 코드(`src/malttara/` 중 ETL 제외, `run.py`)에 표준 라이브러리 밖 import가 없는지 확인한다.

---

## 2. 폴더 구성 (압축을 푼 뒤)

```
malttara-jeju/
├─ run.bat                    ← 더블클릭해서 실행 (Windows)
├─ run.py                     ← 실제 실행 파일 (run.bat이 호출)
├─ .env.example               ← 환경변수 예시 (키 칸이 비어 있음)
├─ .env                       ← 평가용 AI 키 파일 (제출본에만, 4장 참고. 없으면 규칙 기반으로 동작)
├─ requirements.txt           ← 비어 있음 (실행에 필요한 패키지 없음)
├─ requirements-etl.txt       ← 데이터 다시 만들기(ETL)용, 평가 실행에는 불필요
├─ config/                    ← 가중치·권역·관심사 설정(JSON)
├─ src/malttara/              ← 에이전트·Tool·서버 코드, 프롬프트(agent/prompts.py)
├─ data/db/malttara.sqlite    ← 가공 데이터베이스 (제주데이터허브 데이터 가공본, 동봉)
├─ data/db/map.json           ← 화면 지도용 읍면동 경계 (동봉)
├─ web/dist/                  ← 화면 파일 (index.html, js, css, fonts 등, 동봉)
├─ tests/                     ← 자동 테스트
└─ docs/05_submission/        ← 이 매뉴얼, 데이터 활용 명세
```

| 파일 | 없으면 |
|---|---|
| `data/db/malttara.sqlite` | 실행 직후 "데이터 파일이 없습니다" 안내 후 종료 (7장) |
| `data/db/map.json` | 화면 지도만 비어 보인다(경로 생성은 동작) |
| `web/dist/` | 브라우저에 "프론트 빌드(web/dist)가 없습니다" 안내 문구만 보인다 |
| `.env` | AI 키 없음 → 규칙 기반 모드로 전 기능 동작 |

---

## 3. 설치 순서 (최초 1회)

### 3-1. Python 설치
1. https://www.python.org/downloads/ 에서 **Python 3.11 이상**의 Windows installer (64-bit)를 받는다.
2. 설치 첫 화면 아래쪽 **"Add python.exe to PATH"를 체크**한다. ("Use admin privileges when installing py.exe"는 기본값 그대로 둔다.)
3. **Install Now**를 누르고 끝날 때까지 기다린다.
4. 확인: 시작 메뉴에서 "명령 프롬프트"를 열고 아래를 입력한다. `Python 3.11.x` 이상이 나오면 된다.
   ```
   py --version
   ```
   (`py`가 없다고 나오면 `python --version`)

> 관리자 권한은 Python 설치에만 필요할 수 있다. 프로그램 실행에는 필요 없다.

### 3-2. 결과물 압축 풀기
1. 제출 ZIP을 **쓰기 가능한 폴더**(예: `C:\malttara-jeju` 또는 바탕화면)에 **압축 풀기**한다.
2. ZIP 미리보기 창 안에서 바로 실행하지 않는다(쓰기 불가 → 실행 기록 저장 실패). `C:\Program Files` 아래도 피한다.
3. 경로 문제를 피하려면 영문 경로(`C:\malttara-jeju`)를 권장한다.

### 3-3. (선택) AI 키 확인
- 제출본에는 평가용 `.env`가 들어 있다(4장). 따로 할 일은 없다.

추가 설치(`pip install`)는 **하지 않는다.**

---

## 4. 환경변수(.env)와 AI 키

### 4-1. 위치와 읽는 방식
- 파일 위치: **`run.py`와 같은 폴더의 `.env`** (`malttara-jeju\.env`).
- `run.py`가 시작할 때 이 파일을 한 번 읽는다(`src/malttara/config.py`의 `load_env`). `KEY=VALUE` 형식의 줄만 읽고, `#`으로 시작하는 줄은 무시한다.
- 같은 이름의 Windows 환경변수가 있으면 그 값이 우선한다.
- 키 값은 화면·콘솔·로그·DB 어디에도 기록하지 않는다(`agent/llm.py`).
- 키가 비어 있거나 파일이 없으면 **규칙 기반 모드**로 동작한다. 콘솔에 `AI 키 없음 → 규칙 기반으로 동작`이 표시된다.

### 4-2. AI 관련 항목 (`.env.example`과 같은 이름)

| 이름 | 뜻 | 평가용 값(예시 형식, 실제 키는 제출본 `.env`에만) |
|---|---|---|
| `LLM_API_KEY` | 외부 AI API 키 | Anthropic Console(platform.claude.com)에서 발급한 키 (이 문서에는 적지 않는다) |
| `LLM_PROVIDER` | API 종류 | `anthropic` |
| `LLM_BASE_URL` | API 주소 | `https://api.anthropic.com` |
| `LLM_MODEL` | 모델 이름 | `claude-haiku-5-5` (Claude Haiku 5.5) |

- `LLM_API_KEY`와 `LLM_MODEL`이 있어야 AI를 쓴다(`LLM_PROVIDER=anthropic`이면 주소는 비워도 기본값). 하나라도 비면 규칙 기반이다.
- 추가 패키지 없이 Python 표준 라이브러리(`urllib`)로 Anthropic Messages API(`/v1/messages`)를 호출한다.
- AI 호출 1회 제한 시간은 20초, 응답 길이 상한은 1,024토큰(`config/settings.json`의 `llm`). 실패·시간 초과·형식 오류면 그 판단만 규칙으로 바꿔 계속 진행한다.
- 분당 AI 호출은 30회까지(`config/security.json`). 넘으면 규칙으로 처리한다.
- 실제로 쓴 토큰은 DB의 `llm_usage` 표에 남는다. 집계: `py -3 -m malttara.agent.usage` (`src` 폴더를 `PYTHONPATH`에 두고 실행, 비용 설명은 `cost.md`).
- 평가용 키는 **사용 한도를 설정**했고 **평가 종료 후 폐기**한다(대회 규칙의 AI API 키 예외 조항).
- 평가용 키를 직접 넣어야 하는 경우: `.env.example`을 복사해 이름을 `.env`로 바꾸고, 위 표의 값을 채운 뒤 저장한다(메모장 사용 가능, 인코딩 UTF-8).

### 4-3. 데이터 API 키 (평가 실행에는 필요 없음)
- 제주데이터허브 프로젝트키(`HUB_PROJECT_KEY`), 공공데이터포털 서비스키(`DATA_GO_KR_KEY`)는 **제출물에 넣지 않았다**(대회 규칙).
- 이 키들은 **데이터를 처음부터 다시 만들 때(9장)만** 필요하다. 실행 중에는 외부 데이터 API를 호출하지 않는다. 모든 데이터는 `data/db/malttara.sqlite`에 가공해 동봉했다.

---

## 5. 최초 실행

1. 압축을 푼 폴더에서 **`run.bat`을 더블클릭**한다.
2. 검은 콘솔 창이 열리고 아래와 비슷한 줄이 나온다.
   ```
   말따라 제주 실행 중: http://127.0.0.1:8765/  (AI 연결됨)
   끝내려면 이 창에서 Ctrl+C를 누르세요.
   ```
   - `(AI 연결됨)`: `.env`에 AI 설정 세 값이 있음 (실제 연결 여부는 첫 AI 호출 때 확인되며, 실패하면 규칙으로 넘어간다)
   - `(AI 키 없음 → 규칙 기반으로 동작)`: 키 없이 동작
3. 기본 브라우저가 자동으로 `http://127.0.0.1:8765/`를 연다. 안 열리면 브라우저 주소창에 직접 입력한다.
4. 화면 흐름: **01 여행 설명·조건 확인 → 02 경로 만들기 → 03 미리보기(말 타이핑 게임 또는 목록) → 04 다시 짜기·최종 계획**. 화면의 "사용 가이드" 버튼(30초 사용 가이드)을 누르면 단계별 안내가 나온다.
5. **끝내기**: 콘솔 창에서 `Ctrl+C`를 누른 뒤 아무 키나 눌러 창을 닫는다(또는 창의 X).

`run.bat`이 하는 일: 콘솔을 UTF-8로 바꾸고(`chcp 65001`, `PYTHONUTF8=1`) → `py -3 run.py`를 실행, `py`가 없으면 `python run.py` → 둘 다 없으면 Python 설치 안내를 출력하고 멈춘다.

### 명령 프롬프트에서 실행하기 (선택)
```
cd C:\malttara-jeju
py -3 run.py                     실제 데이터로 실행 (기본 포트 8765)
py -3 run.py --port 9000         다른 포트로 실행
py -3 run.py --no-browser        브라우저를 자동으로 열지 않음
py -3 run.py --mock              모의 데이터로 실행 (DB 없이 화면 확인용, 실제 장소 아님)
```
(`py`가 없으면 `python`으로 바꿔 입력)

### 키오스크 운영 팁
- 브라우저에서 `F11`로 전체 화면.
- 서버는 이 PC 안(`127.0.0.1`)에서만 접속되며 외부에 열리지 않는다. 그래서 보통 Windows 방화벽 허용 창이 뜨지 않는다. 뜨면 "취소"해도 동작한다.

---

## 6. 동작 확인 (설치 직후 1분 점검)

| 확인 | 방법 | 기대 결과 |
|---|---|---|
| 서버 상태 | 브라우저에서 `http://127.0.0.1:8765/api/health` | `{"ok": true, "llm_available": true 또는 false, "data_version": "2026-11-19"}` 형태 |
| 경로 생성 | 01 화면에 "2박 3일 바다 보고 싶어요, 여유롭게" 입력 → 02 진행 | 실행 로그가 한 줄씩 나오고 3일 일정 생성 |
| AI 없이 동작 | `.env`의 `LLM_API_KEY=` 값을 지우고 재실행 | 콘솔에 `AI 키 없음 → 규칙 기반으로 동작`, 같은 흐름 완주 |
| 자동 테스트(선택) | 명령 프롬프트에서 아래 명령 | 마지막 줄 `OK` |

```
cd C:\malttara-jeju
set PYTHONPATH=src
py -3 -m unittest discover -s tests -v
```
(인수 테스트 11종만: `py -3 -m unittest tests.test_acceptance -v`)

---

## 7. 오류와 조치

| 증상 | 원인 | 조치 |
|---|---|---|
| `Python 3.11 이상이 필요합니다...` 출력 후 멈춤 | Python 미설치 또는 PATH 미등록 | 3-1을 다시 하되 "Add python.exe to PATH" 체크. 설치 후 `run.bat`을 다시 더블클릭 |
| `python`을 입력하면 Microsoft Store가 열림 | Windows 앱 실행 별칭 | `run.bat`은 `py`를 먼저 쓰므로 보통 문제없다. 계속되면 설정 → 앱 → 고급 앱 설정 → 앱 실행 별칭에서 python.exe·python3.exe 끄기 |
| `포트 8765를 쓸 수 없습니다(이미 실행 중일 수 있습니다)` | 이미 켜진 서버 창이 있거나 다른 프로그램이 포트 사용 | 먼저 열린 말따라 제주 콘솔 창을 닫는다. 그래도 안 되면 명령 프롬프트에서 `py -3 run.py --port 9000` 후 `http://127.0.0.1:9000/` 접속 |
| `데이터 파일이 없습니다: data/db/malttara.sqlite` | 압축이 덜 풀렸거나 DB 파일이 빠짐 | ZIP을 다시 "모두 압축 풀기". `data\db\malttara.sqlite`가 있는지 확인. 화면만 볼 때는 `py -3 run.py --mock` |
| 브라우저가 자동으로 안 열림 | 기본 브라우저 미설정 등 | 콘솔에 나온 주소 `http://127.0.0.1:8765/`를 Chrome·Edge 주소창에 직접 입력 |
| 화면에 "프론트 빌드(web/dist)가 없습니다" | `web/dist` 폴더 누락 | ZIP을 다시 압축 풀기. (개발 저장소라면 `py -3 web/build.py` 실행) |
| 화면이 하얗게 비어 있음 | 브라우저 캐시·구버전 브라우저 | `Ctrl+F5` 새로고침, Chrome/Edge 최신판 사용 |
| 콘솔에 `AI 키 없음 → 규칙 기반으로 동작` | `.env` 없음 또는 키 칸 비어 있음 | 정상 동작(규칙 기반). AI를 쓰려면 4-2대로 `.env` 작성 후 재실행 |
| AI 키가 있는데 각 단계가 오래 걸림(수십 초) | 인터넷 차단·API 장애로 AI 호출이 제한 시간(20초)까지 기다린 뒤 규칙으로 넘어감 | 결과는 정상이다. 오프라인 환경이면 `.env`의 `LLM_API_KEY=`를 비워 처음부터 규칙 기반으로 실행 |
| 경로를 만들 때 "여행 기간이 없습니다" | 입력에 기간이 없음 | "2박 3일", "당일치기"처럼 기간을 넣는다(1~7일) |
| `database is locked` 또는 저장 실패 | 쓰기 불가 폴더(ZIP 내부·Program Files) 또는 서버 두 개 동시 실행 | 쓰기 가능한 폴더로 옮기고 서버 창을 하나만 띄운다 |
| 콘솔 한글이 깨짐 | 콘솔 코드페이지 | `run.bat`으로 실행하면 UTF-8로 맞춘다. 직접 실행할 때는 `chcp 65001` 후 실행 |

---

## 8. 제약사항

- 거리는 장소 사이 **직선거리**다. 도로망 데이터가 없어 이동 시간·도로 거리를 표시하지 않는다.
- 지역 지표(563)는 2018-01~2022-09 내국인 유동인구, 장소 주변 지표(1208)는 2021년 7~12월 토요일 렌터카 표본이다. "현재 혼잡도"가 아니다.
- 부속섬(우도·추자 등)은 추천 범위에서 뺀다.
- 한 번에 한 명의 키오스크 사용자를 가정한다.
- 자세한 데이터 한계는 `docs/05_submission/data_spec.md` 7장.

---

## 9. (개발자용) 데이터 다시 만들기 — 평가 실행에는 필요 없음

제출본에는 가공 DB(`data/db/malttara.sqlite`, `map.json`)가 들어 있어 이 단계가 필요 없다. 원본부터 다시 만들 때만 한다(개발 PC 기준, 563 원본이 약 2.4GB라 수 분 걸린다).

### 9-1. 키 발급 (제출물에 키 없음)
| 키 | 발급 방법 | 용도 |
|---|---|---|
| `HUB_PROJECT_KEY` | 제주데이터허브(https://jejudatahub.net) 회원가입·로그인 → 데이터 상세에서 "프로젝트 담기" → 마이페이지 → 프로젝트 관리 → 프로젝트 상세에서 프로젝트키 확인 | 허브 Open API 811·812 스냅샷 |
| `DATA_GO_KR_KEY` | 공공데이터포털(https://www.data.go.kr) 로그인 → "한국관광공사_국문 관광정보 서비스_GW"(https://www.data.go.kr/data/15101578/openapi.do) 활용신청 → 마이페이지에서 일반 인증키 확인 | TourAPI 분류·개요·음식점 스냅샷 |

받은 키는 `.env`의 같은 이름 칸에만 적는다. 코드·문서에 적지 않는다.

### 9-2. 원본 파일 배치 (`data/raw/`)
허브 파일형 데이터는 허브에 로그인 → 데이터 상세 페이지(`https://jejudatahub.net/data/view/data/{ID}`) → 프로젝트 담기 → 첨부파일 다운로드. 상세: `data/guides/how-to-collect.md`.

| 위치 | 파일 | 받는 곳 |
|---|---|---|
| `data/raw/1349/` | `제주관광공사_제주관광정보시스템(VISIT JEJU)_여행장소.csv` | 허브 1349 |
| `data/raw/563/` | `내국인 유동인구 구성비율.csv` (약 2.4GB) | 허브 563 |
| `data/raw/1208/` | `체류거점_2021_07.csv` ~ `체류거점_2021_12.csv` (6개) | 허브 1208 |
| `data/raw/189/` | `제주특별자치도_내국인관광지입장객수추이.csv` | 허브 189 |
| `data/raw/190/` | `제주특별자치도_외국인관광지입장객수추이.csv` | 허브 190 |
| `data/raw/784/` | `제주특별자치도해수욕장정보.csv` | 허브 784 |
| `data/raw/858/` | `무장애여행정보.csv` | 허브 858 |
| `data/raw/hub_811.json`, `hub_812.json` | 허브 Open API 스냅샷 | 아래 `fetch_hub` 명령으로 생성 |
| `data/raw/tourapi_jeju.json` | TourAPI 스냅샷 | 아래 `fetch_tourapi` 명령으로 생성 |
| `data/raw/boundary/HangJeongDong_ver20261001.geojson` | 행정동 경계 | https://github.com/vuski/admdongkor (ver20261001, CC BY 4.0) |

(912 파일은 권역 이름 확인에만 썼고 DB 빌드에는 쓰지 않는다.)

### 9-3. 명령 (프로젝트 폴더에서)
```
py -3 -m pip install -r requirements-etl.txt
set PYTHONPATH=src
py -3 -m malttara.etl.fetch_hub 811
py -3 -m malttara.etl.fetch_hub 812
py -3 -m malttara.etl.fetch_tourapi
py -3 -m malttara.etl.build_db
```
- `build_db` 기본 경로: 입력 `data/raw`, 출력 `data/db/malttara.sqlite`, `data/db/map.json` (`--raw`, `--db`, `--map`으로 바꿀 수 있음).
- 없는 원본은 그 단계만 건너뛰고 `[건너뜀]` 로그를 남긴다. 끝나면 단계별 건수를 출력하고, 같은 값이 DB `meta.build_stats`에 저장된다.
- 참고: 현재 ETL 코드도 표준 라이브러리만 import한다. `requirements-etl.txt`(pyshp, pyproj)는 경계 파일 형식이 바뀔 때를 대비한 예비 목록이다.
- 데이터 흐름·매칭 결과: `docs/05_submission/data_spec.md`.

---

## 10. 검증 기록 (클린 PC 설치 확인 — 사람이 채운다)

Python 공식 설치본만 있는 Windows(가능하면 다른 PC 또는 새 사용자 계정)에서 ZIP을 풀고 `run.bat` 더블클릭 → 01→04 완주.

| 날짜 | 확인자 | PC·OS | Python 버전 | AI 키 | 결과(01→04 완주) | 걸린 시간 | 문제·조치 |
|---|---|---|---|---|---|---|---|
| | | | | 없음(규칙 기반) | | | |
| | | | | 있음(Claude Haiku 5.5) | | | |
| | | | | 있음 + 인터넷 차단 | | | |

자동 테스트 결과:

| 날짜 | 명령 | 결과 |
|---|---|---|
| 2026-11-19 | `PYTHONPATH=src python -m unittest tests.test_acceptance -v` (개발 PC, Python 3.14, 모의 DB) | 11개 OK |
| | `py -3 -m unittest discover -s tests -v` (클린 PC) | |
