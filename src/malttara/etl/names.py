"""장소 이름 정규화와 유사도(ETL 공용, 표준 라이브러리만)."""
import csv
import difflib
import re

_PAREN = re.compile(r"\([^)]*\)|\[[^\]]*\]|（[^）]*）")
_NON_WORD = re.compile(r"[\W_]+", re.UNICODE)


def normalize_name(name: str, prefixes: list) -> str:
    """괄호와 그 안, 공백, 특수문자를 지우고 접두어(예: '제주')를 뗀 뒤 소문자로."""
    s = _PAREN.sub("", name or "")
    s = _NON_WORD.sub("", s).lower()
    pres = sorted({_NON_WORD.sub("", p).lower() for p in prefixes if p}, key=len, reverse=True)
    changed = True
    while changed:                       # "제주 서귀포 산방산" → "산방산"
        changed = False
        for p in pres:
            # 접두어만 남는 이름('제주')은 지우지 않는다
            if s.startswith(p) and len(s) > len(p):
                s = s[len(p):]
                changed = True
                break
    return s


def name_similarity(a: str, b: str) -> float:
    """정규화(접두어 제외) 후 difflib 비율(0~1)."""
    na, nb = normalize_name(a, []), normalize_name(b, [])
    if not na or not nb:
        return 0.0
    return difflib.SequenceMatcher(None, na, nb).ratio()


def open_csv(path: str):
    """utf-8-sig로 먼저 열어 보고, 깨지면 cp949로 연다. 열린 파일 객체를 돌려준다."""
    try:
        f = open(path, encoding="utf-8-sig", newline="")
        f.read(1 << 16)
        f.seek(0)
        return f
    except UnicodeDecodeError:
        f.close()
    return open(path, encoding="cp949", newline="")


def read_csv_rows(path: str) -> list:
    """CSV 전체를 dict 행 목록으로 읽는다(작은 파일용)."""
    with open_csv(path) as f:
        return list(csv.DictReader(f))


def load_mapping(path: str, key_col: str, val_col: str) -> dict:
    """수작업 매핑표(data/mapping/*.csv)를 {key: value}로 읽는다. 빈 값은 건너뛴다."""
    out = {}
    for row in read_csv_rows(path):
        k, v = (row.get(key_col) or "").strip(), (row.get(val_col) or "").strip()
        if k and v:
            out[k] = v
    return out
