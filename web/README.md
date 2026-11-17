# web/ — 말따라 제주 프론트 (B 트랙)

바닐라 JavaScript(ES 모듈) + SVG. 번들러·Node가 필요 없다. 서버(`run.py`)는 계약대로 `web/dist`를 서빙하므로,
`python web/build.py`가 실행에 필요한 파일(index.html·css·js·fonts)만 `web/dist`로 복사한다. `web/dist`는 빌드 산출물이라 git에 올리지 않고(.gitignore `dist/`), 제출 ZIP에는 넣는다.
외부 네트워크 자원 없음: 글꼴은 `fonts/`에 동봉, 아이콘·말·지도·차트는 모두 코드로 그린 SVG.

## 실행

```bash
# 1) 목업으로 화면만 보기 (서버·DB 없이)
cd web
python -m http.server 8799
# 브라우저: http://127.0.0.1:8799/?mock=1

# 2) A 트랙 서버와 연결 (저장소 루트에서)
python web/build.py          # web/ → web/dist 복사 + 외부 주소 점검
python run.py --mock         # A의 모의 데이터 서버, http://127.0.0.1:8765/
#    파일을 고친 뒤에는 build.py 를 다시 실행하고 브라우저를 새로고침
```

- `?mock=1`이면 `js/mock.js`가 계약과 같은 모양으로 응답한다. 화면 오른쪽 위에 `MOCK DATA` 배지가 뜬다.
- 목업의 장소명(`모의 해변 서부1` 등)과 수치는 모두 가짜다. 실제 데이터로 착각하지 않도록 배지를 지우지 않는다.

## 구조

```
build.py                web/dist 로 복사 (python web/build.py)
index.html              진입점 (type="module")
css/app.css             디자인 토큰·컴포넌트 스타일 (흰 바탕, 회색 선, 청록 데이터 강조)
js/main.js              상태 변경 동작(actions), 헤더, 렌더 루프
js/state.js             전역 상태 하나 + 구독. session_id로 늦게 온 배치 응답 무시
js/api.js               계약 API 래퍼, pollBatch(500ms, 20초 지연 알림)
js/mock.js              목업 서버 (?mock=1)
js/ctx.js               설정·지도·통계 캐시
js/format.js            표시 문구(거리·미반영·위반·반응)
js/dom.js               h()/s() 엘리먼트 헬퍼, 아이콘, 말 그림
js/components/          map.js(SVG 지도) log.js(실행 로그) placecard.js(장소 카드·지표 블록) chart.js(선 차트)
js/screens/step1~4.js   01 여행 설명·조건 확인 / 02 경로 만들기 / 03 미리보기(게임·목록) / 04 다시 짜기·최종
mock/                   목업 픽스처 (map·config·places·stats_emd·trend)
fonts/                  Geist, Geist Mono, Pretendard (모두 SIL OFL 1.1) + 라이선스 파일
```

## 지켜야 할 것 (계획서 Global Constraints)

- 화면 수치는 전부 서버 값. 프론트는 반올림만 한다.
- 거리 표기 `직선 n km (도로거리·이동시간 아님)`.
- 입력 안 한 조건은 `(미반영)`. 지표 없음은 0이 아니라 `지표 없음`.
- 장소 지표는 `{emd} 지표 (읍면동 단위)` / `장소 반경 {r}km 지표` 두 블록으로 분리.
- 03 게임: IME 조합 중에는 판정하지 않음(`isComposing`, keyCode 229). 띄어쓰기 무시 비교.
- 1920×1080 기준, 1366×768에서 가로 스크롤 없음.

## 출처

- 지도 목업 경계(`mock/map.json`): 통계청 SGIS 행정동 경계(공공누리 제1유형)를 vuski/admdongkor가 가공(CC BY 4.0), ver20260701. 제주 41개 행정동(추자면·우도면 제외), 작은 섬 조각 제외 후 단순화.
- 글꼴: Geist·Geist Mono (Vercel, SIL OFL 1.1), Pretendard (길형진, SIL OFL 1.1).

## 키오스크 사용성 원칙 (2026-11-17 점검 반영)

- **한 화면에 결과가 보이게**: 02·04는 왼쪽 날짜별 목록, 오른쪽 지도(고정). 인쇄 버튼은 04 첫 화면에.
- **근거는 접어 두기**: 장소는 한 줄(이름·분류·앞 장소와의 직선거리). `근거 보기`를 누르면 지표 두 블록·설명·대안·출처가 펼쳐진다.
- **AI 실행 로그는 쉬운 말로**: 한국어 단계명이 먼저, Tool 이름은 작게. 실행 중에는 펼치고, 끝나면 `AI가 한 일`로 접힌다(눌러서 다시 볼 수 있음).
- **입력 최소화**: 예시 버튼은 누르면 바로 조건까지 읽는다. Enter = 확인, Shift+Enter = 줄바꿈. 입력 안 한 조건은 한 줄로 따로 모아 `미반영`으로 표시.
- **게임 도착 카드**는 이름·분류·반응 버튼만. 데이터 근거는 목록 모드에서.
- **시연 기능 숨김**: 오류 주입 토글·다시 만들기는 `?demo=1` 또는 `Ctrl+Shift+D`에서만 보인다(심사 시연용).
- **자동 초기화**: 입력이 120초 없으면 15초 안내 후 처음 화면으로(다음 방문객 개인정보 보호).
- 글자 16px 이상, 버튼 높이 44px 이상(주요 버튼 54px).
