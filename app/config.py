"""webpy/config.ini 읽기. [web] host, port / [db] path."""
import configparser
from pathlib import Path

WEBPY_DIR = Path(__file__).resolve().parents[1]
INI_PATH = WEBPY_DIR / "config.ini"

_cfg = configparser.ConfigParser()
_cfg.read(INI_PATH, encoding="utf-8")

HOST: str = _cfg.get("web", "host", fallback="0.0.0.0")
PORT: int = _cfg.getint("web", "port", fallback=8000)

_db = _cfg.get("db", "path", fallback="").strip()
DB_PATH: Path = (WEBPY_DIR / _db).resolve() if _db else WEBPY_DIR.parent / "guard.db"
