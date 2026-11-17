"""한국관광공사_국문 관광정보 서비스_GW(KorService2) 제주 스냅샷 받기(개발 PC 전용).

문서: https://www.data.go.kr/data/15101578/openapi.do (확인일 2026-11-17)
- 기본 주소: https://apis.data.go.kr/B551011/KorService2
- areaBasedList2: 필수 serviceKey·MobileOS·MobileApp, 선택 numOfRows·pageNo·_type·arrange·contentTypeId·
  lDongRegnCd·lDongSignguCd·lclsSystm1~3. areaCode·sigunguCode·cat1~3은 "미사용항목(삭제예정)"
  → 지역은 법정동 시도코드 lDongRegnCd(제주특별자치도 = 50), 분류는 lclsSystm1~3을 쓴다.
- detailCommon2: 필수 contentId → 개요(overview).
- categoryCode2: lclsSystmListYn=Y → 분류체계 전체 코드·이름표.
- 응답 필드 이름(contentid, title, mapx, mapy, lclsSystm3 등)은 첫 실제 호출로 다시 확인한다.

실행: PYTHONPATH=src python -m malttara.etl.fetch_tourapi [--no-overview] [--max-overview N]
키는 .env의 DATA_GO_KR_KEY. 키 값은 출력·기록하지 않는다.
개요는 장소마다 1회 호출이라 일일 한도를 넘을 수 있다. 같은 출력 파일이 있으면 이미 받은 개요는 다시 받지 않는다.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from malttara.config import ROOT, load_env

BASE_URL = "https://apis.data.go.kr/B551011/KorService2"
JEJU_LDONG_REGN_CD = "50"
# 관광지·문화시설·레포츠·쇼핑·음식점
CONTENT_TYPES = {"12": "관광지", "14": "문화시설", "28": "레포츠", "38": "쇼핑", "39": "음식점"}
PAGE_SIZE = 100
SLEEP_S = 0.2
DEFAULT_OUT = os.path.join(str(ROOT), "data", "raw", "tourapi_jeju.json")


class ApiError(Exception):
    """키가 들어간 URL을 메시지에 담지 않는 오류."""


def _call(api_key: str, op: str, params: dict) -> dict:
    """KorService2 호출 → JSON dict. 오류 메시지에 URL(키 포함)을 넣지 않는다."""
    q = {"MobileOS": "ETC", "MobileApp": "malttara", "_type": "json"}
    q.update(params)
    # 공공데이터포털 키는 인코딩된 키(%)와 디코딩된 키가 있다. 인코딩된 키는 다시 인코딩하지 않는다.
    key_part = "serviceKey=" + (api_key if "%" in api_key else urllib.parse.quote(api_key, safe=""))
    url = f"{BASE_URL}/{op}?{key_part}&{urllib.parse.urlencode(q)}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            body = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise ApiError(f"{op} HTTP {e.code}") from None
    except urllib.error.URLError as e:
        raise ApiError(f"{op} 연결 실패: {e.reason}") from None
    finally:
        time.sleep(SLEEP_S)
    try:
        data = json.loads(body)
    except ValueError:
        # 키 오류 등은 XML로 온다. 본문 앞부분만 보여 준다(키는 본문에 없다).
        raise ApiError(f"{op} JSON 아님: {body[:200]!r}") from None
    header = data.get("response", {}).get("header", {})
    if header.get("resultCode") not in (None, "0000", "00"):
        raise ApiError(f"{op} 결과 코드 {header.get('resultCode')}: {header.get('resultMsg')}")
    return data


def _items(data: dict) -> list:
    body = data.get("response", {}).get("body", {})
    items = body.get("items") or {}
    if isinstance(items, dict):
        items = items.get("item") or []
    if isinstance(items, dict):
        items = [items]
    return items if isinstance(items, list) else []


def _total(data: dict) -> int:
    try:
        return int(data.get("response", {}).get("body", {}).get("totalCount") or 0)
    except (TypeError, ValueError):
        return 0


def _paged(api_key: str, op: str, params: dict) -> list:
    out, page = [], 1
    while True:
        q = dict(params, numOfRows=PAGE_SIZE, pageNo=page)
        data = _call(api_key, op, q)
        items = _items(data)
        out.extend(items)
        if not items or len(out) >= _total(data) or len(items) < PAGE_SIZE:
            return out
        page += 1


def fetch_category_names(api_key: str) -> dict:
    """분류체계 코드 → 이름표 {코드: 이름}(1·2·3단계 모두)."""
    names = {}
    for it in _paged(api_key, "categoryCode2", {"lclsSystmListYn": "Y"}):
        for lv in ("1", "2", "3"):
            code, name = it.get(f"lclsSystm{lv}Cd"), it.get(f"lclsSystm{lv}Nm")
            if code and name:
                names[code] = name
        if it.get("code") and it.get("name"):
            names[it["code"]] = it["name"]
    return names


def _load_existing_overviews(out_path: str) -> dict:
    if not os.path.exists(out_path):
        return {}
    try:
        with open(out_path, encoding="utf-8") as f:
            return {r["content_id"]: r["overview"] for r in json.load(f) if r.get("overview")}
    except (ValueError, KeyError, TypeError):
        return {}


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def fetch_tourapi(api_key: str, out_path: str, with_overview: bool = True, max_overview_calls=None) -> int:
    """제주(lDongRegnCd=50) 5개 유형 목록 + 개요를 JSON으로 저장하고 건수를 돌려준다.

    출력 항목: content_id, name, lat, lon, content_type, cat1, cat2, cat3, lclsSystm1~3,
    category(lclsSystm3 이름. cat3는 삭제예정이라 분류체계 코드표로 변환), overview.
    """
    names = fetch_category_names(api_key)
    print(f"분류 코드 {len(names)}개")
    cached = _load_existing_overviews(out_path)
    records = []
    for ct, ct_name in CONTENT_TYPES.items():
        items = _paged(api_key, "areaBasedList2", {"lDongRegnCd": JEJU_LDONG_REGN_CD, "contentTypeId": ct, "arrange": "C"})
        print(f"{ct_name}({ct}) {len(items)}건")
        for it in items:
            l3 = it.get("lclsSystm3") or ""
            records.append({
                "content_id": str(it.get("contentid", "")),
                "name": it.get("title", ""),
                "lat": _to_float(it.get("mapy")),
                "lon": _to_float(it.get("mapx")),
                "content_type": ct_name,
                "cat1": it.get("cat1") or None,
                "cat2": it.get("cat2") or None,
                "cat3": it.get("cat3") or None,
                "lclsSystm1": it.get("lclsSystm1") or None,
                "lclsSystm2": it.get("lclsSystm2") or None,
                "lclsSystm3": l3 or None,
                "category": names.get(l3) or None,
                "overview": cached.get(str(it.get("contentid", ""))),
            })
    if with_overview:
        calls = 0
        for rec in records:
            if rec["overview"] or not rec["content_id"]:
                continue
            if max_overview_calls is not None and calls >= max_overview_calls:
                print(f"개요 호출 상한 {max_overview_calls}회에 도달. 나머지는 다음에 다시 실행하면 이어 받는다.")
                break
            calls += 1
            try:
                its = _items(_call(api_key, "detailCommon2", {"contentId": rec["content_id"]}))
            except ApiError as e:
                print(f"개요 받기 중단: {e}. 받은 데까지 저장한다.")
                break
            if its:
                rec["overview"] = its[0].get("overview") or None
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=1)
    return len(records)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    key = load_env().get("DATA_GO_KR_KEY", "")
    if not key:
        print("DATA_GO_KR_KEY가 비어 있습니다. .env에 공공데이터포털 인증키를 넣은 뒤 다시 실행하세요.")
        return 1
    max_calls = None
    if "--max-overview" in argv:
        max_calls = int(argv[argv.index("--max-overview") + 1])
    try:
        n = fetch_tourapi(key, DEFAULT_OUT, with_overview="--no-overview" not in argv, max_overview_calls=max_calls)
    except ApiError as e:
        print(f"TourAPI 호출 실패: {e}")
        return 1
    print(f"저장: {DEFAULT_OUT} ({n}건)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
