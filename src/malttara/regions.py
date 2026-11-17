"""읍면동 키("{시} {읍면동}") → 권역 판정. config/regions.json만 따른다."""


def region_of_emd(emd, regions_cfg: dict):
    if not emd:
        return None
    for r in regions_cfg["regions"]:
        if emd in r.get("emds", []):
            return r["region_id"]
    si, _, rest = emd.partition(" ")
    for r in regions_cfg["regions"]:
        if r.get("dong_of") == si and rest.endswith("동"):
            return r["region_id"]
    return None


def region_order(regions_cfg: dict) -> list:
    return [r["region_id"] for r in regions_cfg["regions"]]
