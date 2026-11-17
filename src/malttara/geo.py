"""거리·백분위 같은 결정론적 계산."""
import math

EARTH_RADIUS_KM = 6371.0088


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def pct_rank(x: float, values: list) -> float:
    """values 안에서 x보다 작은 값의 비율(0~1). 값이 1개 이하면 0.5(중립)."""
    if len(values) <= 1:
        return 0.5
    return sum(1 for v in values if v < x) / (len(values) - 1)


def centroid(points: list) -> tuple:
    n = len(points)
    return (round(sum(p[0] for p in points) / n, 10), round(sum(p[1] for p in points) / n, 10))
