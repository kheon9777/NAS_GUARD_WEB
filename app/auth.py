"""계정과 세션. 관리자 계정 하나만 둔다 (tbl_user 행 하나). 비밀번호는 PBKDF2-SHA256, 세션은 HMAC 서명 쿠키.
외부 패키지 없이 표준 라이브러리만 쓴다."""
import base64
import hashlib
import hmac
import json
import secrets
import time

from . import db

DEFAULT_USER = "admin"
DEFAULT_PASSWORD = "656530"  # tbl_user가 비어 있을 때 한 번만 넣는 초기 계정. 로그인 후 바꿀 것
SESSION_TTL_S = 12 * 3600
PBKDF2_ITER = 200_000


def _hash(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), PBKDF2_ITER).hex()


def ensure_default_user() -> bool:
    """계정이 하나도 없으면 기본 계정을 만든다. 만들었으면 True."""
    with db.connect() as con:
        if con.execute("SELECT COUNT(*) FROM tbl_user").fetchone()[0] > 0:
            return False
        salt = secrets.token_hex(16)
        con.execute("INSERT INTO tbl_user (username, pw_hash, salt) VALUES (?, ?, ?)",
                    (DEFAULT_USER, _hash(DEFAULT_PASSWORD, salt), salt))
        return True


def verify(username: str, password: str) -> bool:
    with db.connect() as con:
        row = con.execute("SELECT pw_hash, salt FROM tbl_user WHERE username=?", (username,)).fetchone()
    if row is None:
        return False
    return hmac.compare_digest(row["pw_hash"], _hash(password, row["salt"]))


def change_password(username: str, new_password: str) -> None:
    salt = secrets.token_hex(16)
    with db.connect() as con:
        con.execute("UPDATE tbl_user SET pw_hash=?, salt=?, updated_at=strftime('%s','now') WHERE username=?",
                    (_hash(new_password, salt), salt, username))


def user_info(username: str):
    with db.connect() as con:
        return con.execute("SELECT username, datetime(created_at,'unixepoch','localtime') AS created_at,"
                           " datetime(updated_at,'unixepoch','localtime') AS updated_at FROM tbl_user WHERE username=?",
                           (username,)).fetchone()


# ---- 세션 쿠키 ----
def _secret() -> bytes:
    """서명 키. 처음 한 번 만들어 tbl_web_config에 둔다 (재시작해도 로그인이 유지되게)."""
    with db.connect() as con:
        row = con.execute("SELECT value FROM tbl_web_config WHERE key='session_secret'").fetchone()
        if row is None:
            value = secrets.token_hex(32)
            con.execute("INSERT INTO tbl_web_config (key, value) VALUES ('session_secret', ?)", (value,))
            return bytes.fromhex(value)
        return bytes.fromhex(row["value"])


def make_token(username: str) -> str:
    payload = base64.urlsafe_b64encode(json.dumps({"u": username, "exp": int(time.time()) + SESSION_TTL_S}).encode()).decode()
    sig = hmac.new(_secret(), payload.encode(), "sha256").hexdigest()
    return f"{payload}.{sig}"


def read_token(token: str | None) -> str | None:
    """유효하면 username, 아니면 None."""
    if not token or "." not in token:
        return None
    payload, sig = token.rsplit(".", 1)
    if not hmac.compare_digest(hmac.new(_secret(), payload.encode(), "sha256").hexdigest(), sig):
        return None
    try:
        data = json.loads(base64.urlsafe_b64decode(payload.encode()))
    except Exception:
        return None
    if data.get("exp", 0) < time.time():
        return None
    return data.get("u")
