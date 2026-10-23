"""guard.db 연결. guard(C++)와 같은 파일을 WAL 모드로 같이 쓴다."""
import sqlite3

from .config import DB_PATH  # config.ini [db] path. 비우면 프로젝트 루트의 guard.db


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH, timeout=3)  # 잠겨 있으면 3초까지 기다림 (guard의 busy_timeout과 같음)
    con.row_factory = sqlite3.Row
    con.execute("PRAGMA journal_mode=WAL;")
    return con


def table_exists(con: sqlite3.Connection, name: str) -> bool:
    row = con.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name=?", (name,)).fetchone()
    return row is not None


def columns(con: sqlite3.Connection, table: str) -> list[sqlite3.Row]:
    """PRAGMA table_info: cid, name, type, notnull, dflt_value, pk"""
    return con.execute(f"PRAGMA table_info({table});").fetchall()


# ---- 웹 전용 테이블 (guard는 건드리지 않음) ----
SCHEMA = """
CREATE TABLE IF NOT EXISTS tbl_user (
  id         INTEGER PRIMARY KEY,
  username   TEXT NOT NULL UNIQUE,
  pw_hash    TEXT NOT NULL,
  salt       TEXT NOT NULL,
  created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
  updated_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
);
CREATE TABLE IF NOT EXISTS tbl_web_config (
  key   TEXT PRIMARY KEY,
  value TEXT NOT NULL
);
"""


def init_schema() -> None:
    with connect() as con:
        con.executescript(SCHEMA)
