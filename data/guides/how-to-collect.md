# 원본 데이터 받는 법

제주데이터허브 데이터는 제공형태(API / 파일 / 링크)마다 받는 방법이 다르다.
수집 스크립트는 허브 사이트에 접속할 수 있는 PC·서버에서 실행한다.

## 0. 준비: 프로젝트키 (사람이 직접)

1. https://jejudatahub.net 회원가입 → 로그인
2. 마이페이지 → 프로젝트 관리 → **프로젝트 만들기**
3. 쓰려는 데이터의 상세 페이지(`https://jejudatahub.net/data/view/data/{ID}`)에서 **「프로젝트 담기」** → 해당 프로젝트 선택
4. 프로젝트 상세에서 **프로젝트키** 확인 → `.env`의 `HUB_PROJECT_KEY`에 저장 (재발급 버튼 있음)
5. 팀원은 프로젝트 → 멤버 탭 → 멤버 추가로 초대

공식 이용 가이드: https://jejudatahub.net/about/data-use

## 1. Open API (93종)

```
GET https://open.jejudatahub.net/api/proxy/{데이터키}/{프로젝트키}?파라미터
```

- 응답 JSON. 데이터키·요청 변수·응답 필드는 각 카드의 '수집 방법'에, 전체 목록은 `catalog/by-attribute/Open-API-전체.md`에 있다.
- **API마다 일일 호출 한도**(대부분 1,000회, 일부 3,000회). 프로젝트 관리 → 활용데이터 → 「변경 신청」으로 증량 요청 가능.
- 일 단위 API는 `startDate`·`endDate`가 필수 → 기간을 나눠 반복 호출로 과거 데이터를 채운다.
- **먼저 탐색 호출**: API마다 1~2회 호출해 ① 실제 데이터 기간 ② 한 번에 오는 행 수·페이지 처리 여부 ③ 일일 한도로 전체를 받는 데 필요한 일수를 확인한다. 결과는 카드의 `period_actual`과 메모에 기록한다.

```python
import os, requests
BASE = "https://open.jejudatahub.net/api/proxy"
KEY = os.environ["HUB_PROJECT_KEY"]

def call(data_key, **params):
    r = requests.get(f"{BASE}/{data_key}/{KEY}", params=params, timeout=30)
    r.raise_for_status()
    return r.json()
```

## 2. 파일 (670건, 첨부 890개, 약 20GB)

- 로그인 → 프로젝트 담기 → 상세 페이지 첨부파일에서 다운로드 (로그인 세션 필요 → 필요한 파일만 브라우저로 받는 것을 권장)
- 받은 파일은 `raw/{ID}/`에 원본 그대로 저장
- CSV 인코딩이 CP949·UTF-8로 섞여 있으므로 적재 시 통일
- 대용량 목록: `catalog/by-attribute/대용량-파일-50MB-이상.md`

## 3. 링크 (517건)

- 515건이 공공데이터포털(data.go.kr) 원본으로 연결. 파일형은 그 페이지에서 받고, 오픈API형은 data.go.kr 서비스키(`DATA_GO_KR_KEY`) 필요
- 허브 카드에 미리보기가 있으므로 탐색 단계에서는 받지 않아도 된다

## 4. 메타데이터(카탈로그) 갱신

`python scripts/fetch_catalog.py` → `python scripts/build_catalog.py` (scripts/README.md)

## 규칙 메모

- 데이터 API 키는 제출물에 넣지 않는다 (발급 방법만 매뉴얼에)
- 대회 제공 xlsx는 외부 배포 금지
