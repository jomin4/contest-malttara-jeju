"""SQLite 스키마와 조회 함수. 실행 중 코드라 표준 라이브러리만 쓴다."""
import sqlite3

SCHEMA = """
CREATE TABLE IF NOT EXISTS regions (
    region_id TEXT PRIMARY KEY,
    name TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS emd_stats (
    emd TEXT NOT NULL,
    month INTEGER NOT NULL,          -- 0 = 전체 연월 평균
    visit_pop REAL,
    resident_pop REAL,
    visit_ratio REAL,
    period TEXT,
    source_id TEXT,
    PRIMARY KEY (emd, month)
);
CREATE TABLE IF NOT EXISTS places (
    place_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    lat REAL NOT NULL,
    lon REAL NOT NULL,
    emd TEXT,
    region_id TEXT,
    category TEXT,
    category_source TEXT,
    overview TEXT,
    source TEXT,
    quiet_count INTEGER,
    popularity INTEGER,              -- 1349 이용자 기록 수(같은 이름) — 인지도
    in_scope INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS sight_visits (
    place_id TEXT NOT NULL,
    year_month TEXT NOT NULL,
    domestic INTEGER,
    foreign_ INTEGER,
    source_id TEXT
);
CREATE TABLE IF NOT EXISTS data_sources (
    source_id TEXT PRIMARY KEY,
    name TEXT,
    url TEXT,
    fetched_at TEXT,
    period_actual TEXT,
    rows INTEGER,
    license TEXT,
    notes TEXT
);
CREATE TABLE IF NOT EXISTS batches (
    batch_id TEXT PRIMARY KEY,
    kind TEXT,
    prev_batch_id TEXT,
    goal_json TEXT,
    result_json TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS agent_decisions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT,
    point TEXT,
    actor TEXT,
    options_json TEXT,
    choice_json TEXT,
    reason TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS user_interactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT,
    place_id TEXT,
    type TEXT,                       -- virtual_arrival | feedback | itinerary_add | visited
    value TEXT,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS llm_usage (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    batch_id TEXT,
    point TEXT,
    model TEXT,
    input_tokens INTEGER,
    output_tokens INTEGER,
    created_at TEXT
);
CREATE TABLE IF NOT EXISTS meta (
    key TEXT PRIMARY KEY,
    value TEXT
);
CREATE INDEX IF NOT EXISTS idx_places_region ON places(region_id);
CREATE INDEX IF NOT EXISTS idx_sight_place ON sight_visits(place_id);
CREATE INDEX IF NOT EXISTS idx_inter_batch ON user_interactions(batch_id);
"""

PLACE_COLUMNS = ("place_id", "name", "lat", "lon", "emd", "region_id", "category",
                 "category_source", "overview", "source", "quiet_count", "popularity", "in_scope")


def connect(path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(places)")}
    if "popularity" not in cols:                 # 11/19 이전 DB(Release data-2026-11-19 이하)와 호환
        conn.execute("ALTER TABLE places ADD COLUMN popularity INTEGER")
    return conn


def all_places(conn) -> list:
    rows = conn.execute(
        f"SELECT {', '.join(PLACE_COLUMNS)} FROM places WHERE in_scope = 1 ORDER BY place_id"
    ).fetchall()
    return [dict(r) for r in rows]


def emd_stats(conn, month) -> dict:
    """{emd: {visit_pop, resident_pop, visit_ratio, period, source_id, month}}. month None → 0(연평균)."""
    m = 0 if month is None else int(month)
    rows = conn.execute(
        "SELECT emd, month, visit_pop, resident_pop, visit_ratio, period, source_id "
        "FROM emd_stats WHERE month = ? ORDER BY emd", (m,)
    ).fetchall()
    return {r["emd"]: dict(r) for r in rows}


def place_trend(conn, place_id: str) -> list:
    rows = conn.execute(
        "SELECT year_month, domestic, foreign_ AS \"foreign\", source_id FROM sight_visits "
        "WHERE place_id = ? ORDER BY year_month", (place_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def region_names(conn) -> dict:
    return {r["region_id"]: r["name"] for r in conn.execute("SELECT region_id, name FROM regions")}


def data_sources(conn) -> list:
    return [dict(r) for r in conn.execute("SELECT * FROM data_sources ORDER BY source_id")]


def meta_get(conn, key: str):
    r = conn.execute("SELECT value FROM meta WHERE key = ?", (key,)).fetchone()
    return r["value"] if r else None


def meta_set(conn, key: str, value: str) -> None:
    conn.execute("INSERT OR REPLACE INTO meta(key, value) VALUES (?, ?)", (key, value))
