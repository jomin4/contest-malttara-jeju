"""제주데이터허브 Open API 스냅샷 받기: 811 오름 위치 정보, 812 박물관 및 미술관 위치 정보(개발 PC 전용).

호출 형식(data/cards/0811_*.md, 0812_*.md):
  GET https://open.jejudatahub.net/api/proxy/{데이터키}/{프로젝트키}?파라미터
  응답 필드: placeName, category("여행 > 관광,명소 > 오름"), addressJibun, addressDoro, longitude, latitude, placeUrl
카드에 페이지 변수가 적혀 있지 않다. 응답에 hasMore가 있으면 number·limit로 이어 받고,
같은 페이지가 반복되면 멈춘다(첫 탐색 호출로 확인 후 카드 메모에 기록).

실행: PYTHONPATH=src python -m malttara.etl.fetch_hub 811   (또는 812)
키는 .env의 HUB_PROJECT_KEY. 키 값은 출력·기록하지 않는다.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from malttara.config import ROOT, load_env

BASE_URL = "https://open.jejudatahub.net/api/proxy"
DATA_KEYS = {
    "811": "1Dttb1tab8tD88Dtat11111at1t1atD8",
    "812": "at2ta1D1aaa811bata88Dt1D22b1t1bt",
}
PAGE_SIZE = 100
MAX_PAGES = 200
SLEEP_S = 0.2


class HubError(Exception):
    """키가 들어간 URL을 메시지에 담지 않는 오류."""


def _call(project_key: str, data_key: str, params: dict) -> object:
    url = f"{BASE_URL}/{data_key}/{urllib.parse.quote(project_key, safe='')}"
    if params:
        url += "?" + urllib.parse.urlencode(params)
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            body = r.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        raise HubError(f"HTTP {e.code}") from None
    except urllib.error.URLError as e:
        raise HubError(f"연결 실패: {e.reason}") from None
    finally:
        time.sleep(SLEEP_S)
    try:
        return json.loads(body)
    except ValueError:
        raise HubError(f"JSON 아님: {body[:200]!r}") from None


def _rows(data: object) -> list:
    """응답에서 행 목록을 꺼낸다(목록 자체, 또는 dict의 'data' 등 첫 목록 값)."""
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        if isinstance(data.get("data"), list):
            return data["data"]
        for v in data.values():
            if isinstance(v, list):
                return v
    return []


def _last_category(cat: str) -> "str | None":
    """'여행 > 관광,명소 > 오름' → '오름'."""
    parts = [p.strip() for p in (cat or "").split(">") if p.strip()]
    return parts[-1] if parts else None


def _to_float(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def fetch_hub_api(project_key: str, dataset: str, out_path: str) -> int:
    """811/812를 받아 [{name, lat, lon, category}] JSON으로 저장하고 건수를 돌려준다."""
    if dataset not in DATA_KEYS:
        raise ValueError(f"지원하지 않는 dataset: {dataset} (811, 812만)")
    data_key = DATA_KEYS[dataset]
    raw, page, prev_sig = [], 1, None
    while page <= MAX_PAGES:
        data = _call(project_key, data_key, {"number": page, "limit": PAGE_SIZE})
        rows = _rows(data)
        sig = json.dumps(rows[:3], ensure_ascii=False, sort_keys=True)
        if not rows or sig == prev_sig:
            break
        raw.extend(rows)
        prev_sig = sig
        has_more = data.get("hasMore") if isinstance(data, dict) else None
        if not has_more:
            break
        page += 1
    out = []
    for r in raw:
        out.append({
            "name": (r.get("placeName") or "").strip(),
            "lat": _to_float(r.get("latitude")),
            "lon": _to_float(r.get("longitude")),
            "category": _last_category(r.get("category", "")),
        })
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=1)
    return len(out)


def main(argv=None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if not argv or argv[0] not in DATA_KEYS:
        print("사용법: python -m malttara.etl.fetch_hub 811|812")
        return 2
    key = load_env().get("HUB_PROJECT_KEY", "")
    if not key:
        print("HUB_PROJECT_KEY가 비어 있습니다. .env에 제주데이터허브 프로젝트키를 넣은 뒤 다시 실행하세요.")
        return 1
    out_path = os.path.join(str(ROOT), "data", "raw", f"hub_{argv[0]}.json")
    try:
        n = fetch_hub_api(key, argv[0], out_path)
    except HubError as e:
        print(f"허브 API 호출 실패: {e}")
        return 1
    print(f"저장: {out_path} ({n}건)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
