# 말따라 제주 — 최종 결과물

데이터로 **덜 붐비는 제주**를 찾아 주는 여행 경로 AI Agent
제주 AI·빅데이터 활용 AI Agent 개발 챌린지 · 결과물 ZIP

---

## 바로 실행 (Windows)

1. **Python 3.11 이상**을 설치합니다 — https://www.python.org/downloads/ (설치 첫 화면에서 **Add python.exe to PATH** 체크). 추가 패키지 설치는 없습니다.
2. 이 ZIP을 **쓰기 가능한 폴더**(예: 바탕화면)에 "모두 압축 풀기" 합니다. ZIP 미리보기 창 안에서 바로 실행하지 않습니다.
3. 압축을 푼 폴더에서 **`run.bat`을 더블클릭**합니다 → 서버가 켜지고 브라우저에 http://127.0.0.1:8765 가 열립니다.

종료: 검은 콘솔 창을 닫습니다. 문제가 생기면 `docs/05_submission/manual_run.md` 7장(오류와 조치)을 봅니다.

**AI 키**: 동봉한 `.env`에 평가용 Claude(Anthropic) API 키가 들어 있습니다(사용 한도 설정, 평가 종료 후 폐기). 키가 없거나 인터넷이 끊겨도 **규칙 모드로 전 기능이 동작**합니다. 제주데이터허브·공공데이터포털 등 **데이터 API 키는 넣지 않았고**, 실행에도 필요 없습니다(데이터는 가공 DB로 동봉).

## 제출 요건과 위치

| 필수 구분 | 위치 |
|---|---|
| **실행 소스 코드** | `run.bat`·`run.py`(실행), `src/malttara/`(Agent·Tool·서버·ETL), 프롬프트 `src/malttara/agent/prompts.py`, LLM 연동 `src/malttara/agent/llm.py`, 보안 `src/malttara/agent/guard.py`, 설정 `config/`, 화면 `web/dist/`, 가공 DB `data/db/`, 테스트 `tests/` |
| **실행환경·매뉴얼** | 이 README, 설치·실행·오류 `docs/05_submission/manual_run.md`, 화면 사용법 `docs/05_submission/manual_user.md`, 의존성 `requirements.txt`(없음)·`requirements-etl.txt`(데이터 재생성용), 환경변수 예시 `.env.example`, 실행 환경 점검 `docs/05_submission/pc_check.md` |
| **데이터 활용 명세** | `docs/05_submission/data_spec.md`(필수 데이터·출처·이용조건·전처리·분석 흐름), 사용 AI 모델·외부 API·외부 데이터·오픈소스 목록 `docs/05_submission/README.md` |
| **결과 설명자료** | `결과설명자료/말따라제주_결과설명자료.pdf`(문제 정의·Agent 구조·주요 기능·실행 결과·검증·한계·센터 활용), `결과설명자료/말따라제주_데모영상.mp4`(2분 29초 실제 실행 화면), LLM 보안 `docs/05_submission/security.md`, 비용 실측 `docs/05_submission/cost.md`, 원칙 점검 `docs/05_submission/principles_check.md` |
| (참고) 기획서 | `기획서/말따라제주_기획서.pdf` |

## 한눈에 보기

- **무엇을**: 여행을 한 줄로 말하면, 제주데이터허브 데이터(563 읍면동 방문/거주 비율, 1208 렌터카 체류 거점, 1349 여행장소 등)로 관심사에 맞으면서 덜 붐비는 장소를 골라 경로를 짜고, 스스로 검증·수정하고, 말을 타고 미리 둘러본 반응으로 다시 짭니다.
- **AI**: Claude Haiku 5.5가 판단 5곳(조건 해석·작업 계획·수정 행동·유지/교체·설명 다듬기)에서 주어진 선택지 안만 고르고, 수치 계산·검증·적용은 언제나 코드가 합니다. 실패하면 같은 자리를 규칙이 맡습니다.
- **실행 환경**: Python 표준 라이브러리만(`http.server`·`sqlite3`·`urllib`), 외부 CDN 없음, 실행 중 외부 데이터 API 0회. 센터 최소사양(i7-8700 / GTX 1060 / RAM 32GB)에서 동작하며, 3D가 느리면 2D 지도로 자동 전환합니다.

## 검증해 보기

```
:: 자동 테스트 204개 (압축을 푼 폴더에서, 명령 프롬프트)
set PYTHONPATH=src
py -3 -m unittest discover -s tests
```

- 시연 모드: 화면에서 `Ctrl+Shift+D` → 02 화면의 "오류 주입" 켜고 "다시 만들기" → Agent가 위반을 찾아 스스로 고치는 과정이 로그와 "왜 이렇게 짰나요?"에 남습니다.
- 서버 상태: http://127.0.0.1:8765/api/health

## 폴더

```
run.bat · run.py            실행
.env · .env.example         평가용 AI 키 / 환경변수 예시
requirements*.txt           의존성(실행에는 없음)
src/malttara/               Agent·Tool·서버·ETL 코드
config/                     가중치·권역·관심사·보안 설정
data/db/                    가공 DB(malttara.sqlite)·지도(map.json)
web/dist/                   화면
tests/                      자동 테스트
docs/05_submission/         매뉴얼·데이터 활용 명세·보안·비용·명시 사항
결과설명자료/               결과 설명 PDF·시연 영상
기획서/                     기획서 PDF
```

결과물의 권리는 대회 규정에 따라 제주빅데이터센터에 귀속됩니다.
