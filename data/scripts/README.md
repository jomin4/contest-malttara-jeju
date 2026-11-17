# scripts/

`data/` 안의 내용을 다시 만들어내는 코드. 모두 `data/` 폴더에서 실행한다.

| 스크립트 | 하는 일 | 결과 | 상태 |
|---|---|---|---|
| `fetch_catalog.py` | 허브 목록·상세 API로 1,259건 메타데이터 수집 | `catalog/catalog_raw.json` | 사용 가능 |
| `build_catalog.py` | 색인(INDEX·by-category·by-theme·by-attribute·join-keys·series·catalog.jsonl)과 카드 생성. 카드의 메모·분석 결과·status·period_actual은 유지 | `catalog/`, `cards/` | 사용 가능 |
| `collect_api.py` | 프로젝트키로 Open API 원본 수집 (탐색 호출, 일일 한도 관리, 기간 분할) | `raw/` | 구현 단계에서 작성 |
| `load_db.py` | `raw/`의 API 응답·파일을 DB에 적재 (인코딩 통일) | `db/` | 구현 단계에서 작성 |
| `profile.py` | 적재 테이블의 행 수·실제 기간·결측·상위 값 계산 → 카드 '분석 결과'·`status`·`period_actual` 갱신 | `cards/` | 구현 단계에서 작성 |

```bash
cd data
pip install requests
python scripts/fetch_catalog.py     # 카탈로그 갱신 (허브 접속 가능한 네트워크에서)
python scripts/build_catalog.py     # 색인·카드 재생성
```
