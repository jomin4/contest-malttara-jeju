# data/ — 제주데이터허브 데이터 카탈로그

제주데이터허브(jejudatahub.net)에 공개된 데이터 **1,259건 전체**의 메타데이터를 정리한 폴더다.
원본 데이터 자체가 아니라 "어떤 데이터가 있고, 무엇이 들어 있고, 어떻게 받는지"를 찾기 위한 색인과 데이터별 카드가 들어 있다.

- 출처: jejudatahub.net 공개 카탈로그(목록·상세), **수집일 2026-11-15**
- 범위: 제주데이터허브 공개 데이터만. 제주빅데이터센터 데이터는 포함하지 않음
- 원본(API 응답·파일)과 DB는 아직 비어 있음 (`raw/`, `db/`)

## 탐색 순서

1. **[catalog/INDEX.md](catalog/INDEX.md)** — 전체 규모, 분야별 건수, 어떤 색인을 볼지 안내 (몇 KB)
2. 질문에 맞는 색인 하나를 연다

| 질문 | 색인 |
|---|---|
| 분야별로 무엇이 있나 | `catalog/by-category/` (분야 8개) |
| 특정 주제(버스, 유동인구, 관광 수요, 소비 …)의 데이터 | `catalog/by-theme/` (주제군 16개) |
| API로 받을 수 있는 것, 최근 데이터, 좌표·읍면동 단위, 대용량 파일 | `catalog/by-attribute/` |
| 이 데이터와 엮을 수 있는 데이터 (날짜·읍면동·정류소·관광지명·좌표 등) | `catalog/join-keys/` |
| 같은 형식 반복 데이터 (무장애여행 150건, 분석 주제 매쉬업 등) | `catalog/series.md` |
| 여러 조건을 조합한 검색 | `catalog/catalog.jsonl` (아래 jq 예시) |

3. 필요한 카드만 연다: **`cards/{ID 4자리}_*.md`** (예: `cards/0583_*.md`)

모든 색인 파일은 한 번에 읽을 수 있는 크기(60KB 이하)로 나눠져 있다.

## 카드 구성

```
---  frontmatter (id, title, category, type, period_meta, period_actual, auto_update, update_cycle,
     spatial, temporal, join_keys, themes, series, owner, status, url)
---
## 요약 / ### 원문 설명
## 수집 방법      API 주소·요청 변수·응답 필드 / 파일 목록 / 외부 링크
## 컬럼
## 샘플           사이트 미리보기 최대 5행
## 분석 결과       원본 적재 후 채움 (지금은 비어 있음)
## 메모           <!-- notes:start --> ~ <!-- notes:end --> 안에 자유롭게 기록 (재생성해도 유지)
```

`status`: `meta-only`(메타데이터만) → `collected`(원본 수집됨) → `loaded`(DB 적재됨)

## catalog.jsonl 조건 검색 예시

```bash
# API이면서 읍면동 단위인 데이터
jq -c 'select(.type|test("API")) | select(.spatial=="읍면동") | {id,title,period_meta}' catalog/catalog.jsonl

# 관광 수요 주제이면서 2023년 이후까지 있는 데이터
jq -c 'select(.themes|index("관광 수요·방문객")) | select(.end_year|test("^20(2[3-9])|계속")) | {id,title,type,period_meta}' catalog/catalog.jsonl

# '읍면동'과 '날짜(일)' 키를 모두 가진 데이터 (결합 후보)
jq -c 'select((.join_keys|index("읍면동")) and (.join_keys|index("날짜(일)"))) | {id,title,type}' catalog/catalog.jsonl
```

## 해석 규칙 (중요)

- **수치는 카드의 '분석 결과' 또는 DB 조회 결과로만 말한다.**
- `period_meta`는 사이트에 적힌 기간이다. 일 단위 API 중 상당수는 "2015-01-01 ~ 2015-01-01"처럼 시작일만 적혀 있어 **실제 기간은 탐색 호출로 확인**해야 한다.
- `spatial`, `temporal`, `join_keys`, `themes`는 **컬럼명·제목으로 추정한 값**이다. 결합 전에는 카드 샘플로 키 값 형식을 확인한다.
- `auto_update: true` 480건 중 다수는 공공데이터포털 링크형이다. 실제로 갱신되는 API는 그보다 적다.
- 상세 근거와 한계: [guides/methodology.md](guides/methodology.md)

## 폴더

```
data/
├─ README.md            이 파일
├─ catalog/             색인 (INDEX, by-category, by-theme, by-attribute, join-keys, series, catalog.jsonl, catalog_raw.json)
├─ cards/               데이터별 카드 1,259개
├─ guides/              how-to-collect.md (원본 받는 법), methodology.md (조사 방법·한계)
├─ scripts/             카탈로그 수집·카드 생성 스크립트 (scripts/README.md)
├─ raw/                 수집한 원본 [git 제외]
└─ db/                  적재한 DB [git 제외]
```
