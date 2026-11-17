# 05 제출 (배포)

## 제출 체크리스트

### 기획서
- [ ] `docs/02_proposal/` 필수 5개 항목 충족, 15쪽 이내, PDF 변환

### 결과물 ZIP (`submission/`에 빌드)
- [ ] **실행 소스 코드**: Agent 실행 코드, Prompt, Tool/API 연동·데이터 처리 코드, 사용 모델·라이브러리 정보
- [ ] **실행환경·매뉴얼**: README, 설치·실행 절차, 의존성 목록, 환경변수 예시(.env.example), 사용자 매뉴얼, 오류·제약사항
- [ ] **데이터 활용 명세**: 필수 데이터 1종 이상 사용 내역, 출처·이용조건, 전처리·분석 흐름, 외부 데이터·오픈소스 목록
- [ ] **결과 설명자료**: 문제 정의, Agent 구조, 주요 기능, 실행 결과, 검증 방법·한계, 센터 활용 방안

### 규칙 점검
- [ ] 허브 프로젝트키 등 데이터 API 키 미포함, 발급·설정 방법은 매뉴얼에 기재
- [ ] 평가용 외부 AI API 키를 넣는다면 사용 한도 설정, 평가 후 폐기 계획
- [ ] 개인정보·민감정보 미포함
- [ ] 사용 AI 모델 / AI 활용 범위 / 외부 API·서비스 / 외부 데이터 / 오픈소스·외부 코드 명시 (아래 기록 표)
- [ ] 센터 PC 사양(VRAM 3GB)에서 실행 가능, 클린 환경 설치 테스트 완료
- [ ] 대회 제공 xlsx 등 배포 금지 파일 미포함

### 제출
- [ ] 대회 페이지 [갤러리] → [기획서 및 최종 결과물 제출], **11/20 08:00까지** (마감 10:00)
- [ ] 팀이면 팀장이 "팀으로 전환" 완료
- [ ] 제출 후 11/23~27 상호평가 기간에 최소 투표 수 채우기

## 명시 사항 기록 (작업하면서 누적)

| 구분 | 이름 | 용도 | 출처/라이선스 |
|---|---|---|---|
| 사용 AI 모델 | Upstage Solar Pro 4 (`solar-pro4`) | 목표 해석·작업 계획·수정 행동·유지교체 판단·설명 문장 (D5) | 유료 API |
| AI 활용 범위 (개발 도구 포함) | Claude Code + superpowers | 기획·설계·구현 보조 | |
| 외부 API·서비스 | Upstage API (`api.upstage.ai/v1`) | LLM 호출 (실패 시 규칙 기반 폴백) | 약관 확인 필요 |
| 외부 데이터 | 한국관광공사 TourAPI 국문 관광정보 (공공데이터포털) | 장소 분류·개요 보완, 음식점 목록 (빌드 시점 ETL만) | 공공누리 유형 확인 필요 |
| 외부 데이터 | 읍면동 행정경계 (VWorld 또는 SGIS, 선정 전) | SVG 지도 (빌드 시점 변환·동봉) | 재배포 조건 확인 필요 |
| 오픈소스·외부 코드 | (UI) Tailwind CSS(빌드 설치), 아이콘 SVG(Material Symbols 등, 선정 전), 한글 글꼴(Pretendard 후보, OFL) | 프로토타입 기반 화면 | design/ui-prototype/README.md 3장 |
| 디자인 시안 | design/ui-prototype (외부 디자인 도구 생성) | 화면 구성 참고 | 생성 도구·이미지 출처 기록 필요 |
| 외부 데이터 | 행정동 경계 vuski/admdongkor (원자료 통계청 SGIS) — 실서버 ver20261001, B 목업 ver20260701 | 지도 경계 (`data/db/map.json`, B 목업 `web/mock/map.json`) | 원자료 공공누리 제1유형, 가공본 CC BY 4.0. 출처 문구: "본 데이터는 통계청 통계지리정보서비스(SGIS, https://sgis.kostat.go.kr)에서 공공누리 제1유형으로 개방한 행정동 경계를 가공한 것이며(가공: vuski/admdongkor, https://github.com/vuski/admdongkor), CC BY 4.0으로 배포됩니다." |
| 오픈소스·외부 코드 | Geist, Geist Mono (vercel/geist-font) | 화면 글꼴(라틴·숫자·로그) `web/fonts/` | SIL OFL 1.1 |
| 오픈소스·외부 코드 | Pretendard (orioncactus/pretendard) | 화면 글꼴(한글) `web/fonts/` | SIL OFL 1.1 |
| 오픈소스·외부 코드 | (개발용) shapely | `web/tools/make_mock.py` 목업 지도 생성, 실행 중 미사용 | BSD-3-Clause |
