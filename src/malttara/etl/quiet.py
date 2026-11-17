"""1208(월별 렌터카 체류 거점 위치) → 장소 반경 안 체류 거점 수(표준 라이브러리만).

장소 주변 지표(indicators.nearby)다. 읍면동 지표(563)와 섞지 않는다.
"""
import csv
import math

from malttara.geo import haversine_km
from malttara.etl.names import open_csv

CELL_DEG = 0.01


def read_1208_points(paths: list):
    """여러 1208 CSV에서 (위도, 경도)를 차례로 낸다. 좌표가 비었거나 숫자가 아니면 건너뛴다."""
    for path in paths:
        with open_csv(path) as f:
            for row in csv.DictReader(f):
                try:
                    lat, lon = float(row["latitude"]), float(row["longitude"])
                except (KeyError, TypeError, ValueError):
                    continue
                yield lat, lon


def _cell(lat: float, lon: float) -> "tuple[int, int]":
    return math.floor(lat / CELL_DEG), math.floor(lon / CELL_DEG)


def quiet_counts(places: list, points, radius_km: float) -> dict:
    """장소마다 반경 radius_km 안의 점 개수 {place_id: count}.

    0.01° 격자 버킷으로 후보를 좁힌 뒤 하버사인으로 센다. 반경 안에 점이 없으면 0.
    장소가 점 분포의 bbox(+반경) 밖이면 키를 넣지 않는다(→ 지표 없음).
    """
    grid = {}
    min_lat = min_lon = math.inf
    max_lat = max_lon = -math.inf
    for lat, lon in points:
        grid.setdefault(_cell(lat, lon), []).append((lat, lon))
        min_lat, max_lat = min(min_lat, lat), max(max_lat, lat)
        min_lon, max_lon = min(min_lon, lon), max(max_lon, lon)
    if not grid:
        return {}

    dlat = radius_km / 111.0
    out = {}
    for p in places:
        plat, plon = float(p["lat"]), float(p["lon"])
        dlon = radius_km / (111.0 * max(math.cos(math.radians(plat)), 1e-6))
        if not (min_lat - dlat <= plat <= max_lat + dlat and min_lon - dlon <= plon <= max_lon + dlon):
            continue
        c_lat0, c_lon0 = _cell(plat - dlat, plon - dlon)
        c_lat1, c_lon1 = _cell(plat + dlat, plon + dlon)
        n = 0
        for ci in range(c_lat0, c_lat1 + 1):
            for cj in range(c_lon0, c_lon1 + 1):
                for lat, lon in grid.get((ci, cj), ()):
                    if haversine_km(plat, plon, lat, lon) <= radius_km:
                        n += 1
        out[p["place_id"]] = n
    return out
