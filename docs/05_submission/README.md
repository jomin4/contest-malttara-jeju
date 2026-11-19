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
| 외부 데이터 | 행정동 경계 vuski/admdongkor ver20261001 (원자료 통계청 SGIS) | 좌표→행정동 판정, SVG 지도 (빌드 시점 변환·동봉) | CC BY 4.0 (원자료 공공누리 1유형), 출처 표기 |
| 오픈소스·외부 코드 | (UI) Tailwind CSS(빌드 설치), 아이콘 SVG(Material Symbols 등, 선정 전), 한글 글꼴(Pretendard 후보, OFL) | 프로토타입 기반 화면 | design/ui-prototype/README.md 3장 |
| 디자인 시안 | design/ui-prototype (외부 디자인 도구 생성) | 화면 구성 참고 | 생성 도구·이미지 출처 기록 필요 |
| 외부 데이터 | 행정동 경계 vuski/admdongkor ver20260701 (원자료 통계청 SGIS) | B 프론트 목업 지도 `web/mock/map.json` (개발용, 제출 dist에는 미포함) | CC BY 4.0 (원자료 공공누리 1유형), 출처 표기 |
| 오픈소스·외부 코드 | Geist, Geist Mono (vercel/geist-font) | 화면 글꼴(라틴·숫자·로그) `web/fonts/` | SIL OFL 1.1 |
| 오픈소스·외부 코드 | Pretendard (orioncactus/pretendard) | 화면 글꼴(한글) `web/fonts/` | SIL OFL 1.1 |
| 오픈소스·외부 코드 | (개발용) shapely | `web/tools/make_mock.py` 목업 지도 생성, 실행 중 미사용 | BSD-3-Clause |
| 오픈소스·외부 코드 | three.js r187 (mrdoob/three.js) | 03 미리보기 3D 지형 지도 `web/vendor/three/` (로컬 동봉) | MIT |
| 오픈소스·외부 코드 | qrcode-generator 2.0.4 (Kazuhiko Arase) | 04 일정 QR(휴대폰으로 가져가기) `web/vendor/qrcode/` (로컬 동봉) | MIT |
| 외부 데이터 | Copernicus DEM GLO-30 (타일 N33 E126) | 03 미리보기 3D 지형 높이 `web/assets/terrain.bin` (약 250m 격자로 가공·동봉) | © DLR e.V. 2010-2014, © Airbus Defence and Space GmbH 2014-2018, provided under COPERNICUS by the European Union and ESA. 화면에 출처 표기 |
| (정정·B 2026-11-19) 오픈소스·외부 코드 | 화면 구현 방식 | 위의 "(UI) Tailwind CSS·Material Symbols" 줄은 초기 계획. **최종 화면은 바닐라 JavaScript(ES 모듈)·직접 쓴 CSS로 구현, Tailwind·Material Symbols·외부 아이콘 미사용**. 아이콘은 직접 그린 SVG 선 아이콘(`web/js/dom.js`), 말 3D 모델은 three.js 기본 도형으로 직접 구성 | 자체 작성 |
| (정정·B 2026-11-19) 디자인 시안 | design/ui-prototype | 초기 화면 구성 참고로만 사용. 제출 화면(`web/`)에는 시안의 코드·이미지를 포함하지 않음 | — |
| AI 활용 범위 (개발 도구 포함) | Claude (Anthropic) — Claude Code·Cowork | B 화면 구현·리팩터링, 자동 테스트 스크립트, 원칙 점검, 매뉴얼·기획서 초안 작성 보조. 실행 중 화면은 Claude를 호출하지 않음 | 개발 도구 |
| 오픈소스·외부 코드 | (개발용) Playwright | 화면 자동 점검 `web/tools/e2e_scenarios.js`·`tour_walkthrough.js`·`check_responsive.js`, 매뉴얼 스크린샷. 실행·제출 동작에 불필요 | Apache-2.0 |
| 외부 데이터 | (확인) 화면에 표시하는 출처 | 지도 아래 "SGIS 행정동 경계(가공: vuski/admdongkor)", 3D 지도 아래 Copernicus DEM 출처, 근거 패널에 제주데이터허브 데이터 ID(563·1208·189·190·1349)와 기간 표시 | 출처 표기 의무 이행 |
