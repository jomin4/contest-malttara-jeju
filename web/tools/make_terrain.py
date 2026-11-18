"""제주 본섬 높이 격자 생성 (개발용, 실행 중 미사용).

원자료: Copernicus DEM GLO-30 타일 N33 E126 (30m, 1°×1°)
  https://copernicus-dem-30m.s3.amazonaws.com/Copernicus_DSM_COG_10_N33_00_E126_00_DEM/Copernicus_DSM_COG_10_N33_00_E126_00_DEM.tif
출력: web/assets/terrain.bin (Int16 LE, 행=북→남, 열=서→동, 단위 m), web/assets/terrain.json
사용: python web/tools/make_terrain.py <다운로드한 tif> web/assets   (tifffile, imagecodecs, numpy 필요)
"""
import json, sys
import numpy as np
import tifffile

SRC, OUT = sys.argv[1], sys.argv[2]
LON0, LON1, LAT0, LAT1 = 126.10, 127.00, 33.10, 33.62   # 서, 동, 남, 북
F = 9                                                   # 30m × 9 ≈ 0.0025° 평균 풀링

page = tifffile.TiffFile(SRC).pages[0]
a = page.asarray().astype(np.float32)
sx, sy, _ = page.tags[33550].value
_, _, _, ox, oy, _ = page.tags[33922].value
c0, c1 = int(round((LON0 - ox) / sx)), int(round((LON1 - ox) / sx))
r0, r1 = int(round((oy - LAT1) / sy)), int(round((oy - LAT0) / sy))
sub = a[r0:r1, c0:c1]
rows, cols = sub.shape[0] // F, sub.shape[1] // F
sub = sub[:rows * F, :cols * F].reshape(rows, F, cols, F).mean(axis=(1, 3))
sub = np.clip(np.round(sub), 0, 32767).astype("<i2")
sub.tofile(f"{OUT}/terrain.bin")
meta = {
    "west": LON0, "north": LAT1, "dlon": sx * F, "dlat": sy * F, "cols": cols, "rows": rows,
    "max_m": int(sub.max()), "unit": "m",
    "source": "Copernicus DEM GLO-30 (N33 E126)",
    "attribution": "지형: Copernicus DEM GLO-30 © DLR e.V. 2010-2014, © Airbus Defence and Space GmbH 2014-2018, provided under COPERNICUS by the European Union and ESA",
}
json.dump(meta, open(f"{OUT}/terrain.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(meta["cols"], meta["rows"], meta["max_m"])
