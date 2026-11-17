"""설정(config/*.json)과 .env 읽기."""
import json
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG_DIR = ROOT / "config"


def load_config(name: str) -> dict:
    with open(CONFIG_DIR / f"{name}.json", encoding="utf-8") as f:
        return json.load(f)


def load_env(path: str = ".env") -> dict:
    """KEY=VALUE 줄만 읽는다. os.environ 값이 있으면 그것이 우선한다."""
    p = Path(path)
    if not p.is_absolute() and not p.exists():
        p = ROOT / path
    if not p.exists():
        return {}
    out = {}
    for line in p.read_text(encoding="utf-8-sig").splitlines():
        s = line.strip()
        if not s or s.startswith("#") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        k, v = k.strip(), v.strip()
        if len(v) >= 2 and v[0] == v[-1] and v[0] in "\"'":
            v = v[1:-1]
        out[k] = os.environ.get(k, v)
    return out
