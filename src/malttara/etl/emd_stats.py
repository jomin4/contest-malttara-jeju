"""563(내국인 유동인구 구성비율) → 읍면동 × 월 집계(표준 라이브러리만).

원본은 읍면동 × 시간대 × 성·연령 행이고 약 2.4GB라 csv 모듈로 한 줄씩 읽는다.
읍면동 지표는 지역 단위 통계다. 개별 장소의 속성으로 쓰지 않는다(indicators.region).
"""
import csv
import re

from malttara.etl.names import open_csv

SOURCE_ID = "563"


def _year_month(v: str) -> "tuple[int, int] | None":
    """'201801' / '2018-01' / '2018.01' → (2018, 1)."""
    digits = re.sub(r"\D", "", v or "")
    if len(digits) < 6:
        return None
    y, m = int(digits[:4]), int(digits[4:6])
    if not 1 <= m <= 12:
        return None
    return y, m


def _num(v) -> float:
    try:
        return float(str(v).replace(",", "").strip() or 0)
    except ValueError:
        return 0.0


def _row(emd: str, month: int, visit: float, resident: float, period: str) -> dict:
    return {
        "emd": emd,
        "month": month,
        "visit_pop": visit,
        "resident_pop": resident,
        "visit_ratio": (visit / resident) if resident else None,
        "period": period,
        "source_id": SOURCE_ID,
    }


def aggregate_563(csv_path: str, alias: dict) -> list:
    """읍면동 × 월 집계 행 목록.

    1) 같은 (emd, 연월)의 visit_population_count·residence_population_count를 모두 더한다.
    2) (emd, 월)별로 연월 합의 평균 → month 1~12 행.
    3) (emd)별로 전체 연월 합의 평균 → month 0 행.
    visit_ratio = visit_pop / resident_pop (resident 0이면 None).
    period는 파일 전체의 실제 최소~최대 연월("YYYY-MM~YYYY-MM").
    """
    sums = {}  # (emd, (y, m)) → [visit, resident]
    with open_csv(csv_path) as f:
        for row in csv.DictReader(f):
            ym = _year_month(row.get("base_year_month", ""))
            raw = (row.get("emd_name") or "").strip()
            if ym is None or not raw:
                continue
            emd = alias.get(raw, raw)
            acc = sums.get((emd, ym))
            if acc is None:
                acc = sums[(emd, ym)] = [0.0, 0.0]
            acc[0] += _num(row.get("visit_population_count"))
            acc[1] += _num(row.get("residence_population_count"))
    if not sums:
        return []
    yms = sorted({ym for _, ym in sums})
    period = f"{yms[0][0]:04d}-{yms[0][1]:02d}~{yms[-1][0]:04d}-{yms[-1][1]:02d}"

    by_month = {}  # (emd, m) → [[visit, resident], ...]
    by_emd = {}    # emd → [[visit, resident], ...]
    for (emd, (y, m)), acc in sums.items():
        by_month.setdefault((emd, m), []).append(acc)
        by_emd.setdefault(emd, []).append(acc)

    def mean(vals: list, i: int) -> float:
        return sum(v[i] for v in vals) / len(vals)

    out = []
    for emd in sorted(by_emd):
        vals = by_emd[emd]
        out.append(_row(emd, 0, mean(vals, 0), mean(vals, 1), period))
        for m in range(1, 13):
            mv = by_month.get((emd, m))
            if mv:
                out.append(_row(emd, m, mean(mv, 0), mean(mv, 1), period))
    return out
