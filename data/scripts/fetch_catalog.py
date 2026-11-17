"""제주데이터허브 공개 카탈로그(목록 + 상세) 수집 → catalog/catalog_raw.json

사용법 (data/ 폴더에서):  python scripts/fetch_catalog.py
- 인증 불필요. 사이트 데이터 목록 화면이 쓰는 내부 API를 호출한다 (공식 문서 없음 → 하루 1회 수준으로만).
- 상세 호출에 viewCount 파라미터를 붙이지 않아 조회수를 올리지 않는다.
- 동시 3건, 요청 간 0.15초 대기, 실패 시 3회 재시도.
"""
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import requests

BASE = "https://jejudatahub.net"
OUT = Path(__file__).resolve().parent.parent / "catalog" / "catalog_raw.json"
LIST_URL = (BASE + "/api/data?includedKeywords=&excludedKeywords=&categories=&userId=&dataType=&orderBy=createAt"
            "&authYn=false&autoUpdateYn=false&keyword=&keywordOrTagFlag=keyword&isPaging=true&start=0&pageNumber=1&length=5000")
S = requests.Session()
S.headers["User-Agent"] = "jeju-agent-challenge catalog fetcher"


def cut(v, n):
    if v is None:
        return v
    s = str(v)
    return s[:n] + "…" if len(s) > n else v


def detail(i):
    for t in range(3):
        try:
            r = S.get(f"{BASE}/api/data/view", params={"id": i, "userId": ""}, timeout=30)
            r.raise_for_status()
            d = r.json()
            time.sleep(0.15)
            return i, d
        except Exception:
            time.sleep(1.5 * (t + 1))
    return i, None


def main():
    lst = S.get(LIST_URL, timeout=60).json()["data"]
    print("목록", len(lst))
    with ThreadPoolExecutor(max_workers=3) as ex:
        details = dict(ex.map(detail, [x["id"] for x in lst]))
    failed = [i for i, d in details.items() if d is None]
    print("상세 실패", failed)

    out = []
    for x in lst:
        d = details.get(x["id"]) or {}
        prev = d.get("csvData")
        if isinstance(prev, list):
            prev = [[cut(c, 60) for c in r[:40]] if isinstance(r, list) else cut(r, 400) for r in prev[:6]]
        else:
            prev = cut(prev, 1500)
        api = x.get("dataApi")
        out.append({
            "id": x["id"], "key": x["dataKey"], "cat": x["categoryName"], "title": x["title"], "desc": x["description"],
            "start": x["startDate"], "end": x["endDate"], "auto": x["autoUpdateYn"], "period": x["autoUpdatePeriod"],
            "auth": x["authYn"], "views": x["viewCount"], "fav": x["totalFavCount"], "created": x["createAt"],
            "updated": x["updateAt"], "owner": x["owner"], "tag": d.get("tag"),
            "api": {"url": api["url"], "fmt": api["dataFormat"], "method": api["methodType"], "quota": api["quota"],
                    "el": [[e["type"], e["name"], e["description"], e["paramType"], e["requireYn"], e["example"]]
                           for e in api.get("dataApiElements") or []]} if api else None,
            "link": (x.get("dataLink") or {}).get("url"),
            "files": [[f["fileName"], f["fileSize"], f["downloadCount"], f["createAt"]]
                      for f in ((x.get("dataFile") or {}).get("fileInfos") or [])],
            "sample": [[f["fileName"], f["fileSize"]] for f in ((x.get("file") or {}).get("fileInfos") or [])],
            "infoG": len(x.get("infographicGeneral") or []), "infoM": len(x.get("infographicMultimedia") or []),
            "preview": prev,
        })
    OUT.write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print("저장", OUT, len(out))


if __name__ == "__main__":
    main()
