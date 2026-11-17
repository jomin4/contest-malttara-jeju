"""테스트 공용 헬퍼."""
import os
import tempfile

from malttara.config import load_config
from malttara.db import connect
from malttara.etl.mock_data import build_mock_db
from malttara.tools.goal import empty_goal

S = load_config("settings")
I = load_config("interests")
R = load_config("regions")


def goal(**kw) -> dict:
    g = empty_goal()
    g.update({"days": 3, "nights": 2})
    g.update(kw)
    if "days" in kw and "nights" not in kw and kw["days"] is not None:
        g["nights"] = kw["days"] - 1
    return g


def mock_conn():
    path = os.path.join(tempfile.mkdtemp(), "mock.sqlite")
    build_mock_db(path)
    return connect(path), path
