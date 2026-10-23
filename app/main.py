"""guard 웹 콘솔. 설정(tbl_config_info), 화이트리스트, 장비 목록, 계정을 본다/고친다.
실행: webpy/run.sh  (또는 .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000)
"""
from pathlib import Path
from urllib.parse import quote

from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

from . import auth, db, guardctl

app = FastAPI(title="guard console", docs_url=None, redoc_url=None)
templates = Jinja2Templates(directory=str(Path(__file__).parent / "views"))

# 설정 컬럼 설명 (settings.h와 같은 내용). 표에 없는 컬럼은 이름만 보인다
SETTING_HELP = {
    "tcp_rate_window_s": "감시 창 (초)", "tcp_rate_threshold": "창 안에 ACK 없는 패킷 N개 이상이면 차단",
    "icmp_rate_window_s": "감시 창 (초)", "icmp_rate_threshold": "창 안에 echo request N개 이상이면 차단",
    "max_horizen": "IP당 보관하는 이벤트 상한",
    "block_timeout_s": "차단 유지 시간 (초)",
    "nft_family": "nft family", "nft_table": "nft 테이블 이름", "nft_set": "nft set 이름",
    "nft_chain": "nft 체인 이름", "nft_priority": "nft 체인 우선순위",
    "loop_timeout_ms": "epoll 최대 대기 (ms)", "expire_interval_s": "만료 정리 타이머 주기 (초)",
    "mem_log_every_ticks": "메모리 로그 주기 (틱)", "log_path": "로그 파일 경로",
    "device_expire_s": "안 보인 장비 삭제까지 시간 (초, 0이면 안 지움)",
    "arp_spoof_window_s": "감시 창 (초)", "arp_spoof_threshold": "창 안에 같은 IP의 MAC이 N번 이상 바뀌면 알람",
    "log_keep_days": "날짜별 로그 파일 보관 일수 (0이면 안 지움)",
}
RESTART_ONLY = {"nft_family", "nft_table", "nft_set", "nft_chain", "nft_priority", "log_path"}
# 설정 페이지 묶음. (제목, 컬럼 목록). 여기 없는 컬럼은 맨 아래 "기타"로
SETTING_GROUPS = [
    ("TCP 연속 요청", ["tcp_rate_window_s", "tcp_rate_threshold"]),
    ("ICMP 플러드", ["icmp_rate_window_s", "icmp_rate_threshold"]),
    ("차단", ["block_timeout_s"]),
    ("장비 감지", ["device_expire_s"]),
    ("ARP 스푸핑", ["arp_spoof_window_s", "arp_spoof_threshold"]),
    ("로그", ["log_keep_days"]),
]
# 웹에서 숨기는 설정. DB 컬럼과 guard 코드는 그대로이고 sqlite3로는 바꿀 수 있다.
#  - 포트 스캔: 미구현
#  - nft_*, loop_timeout_ms, expire_interval_s, mem_log_every_ticks, max_horizen, log_path: 내부 상수. 운영자가 만질 값이 아님
HIDDEN = {
    "scan_window_s", "scan_threshold",
    "nft_family", "nft_table", "nft_set", "nft_chain", "nft_priority",
    "loop_timeout_ms", "expire_interval_s", "mem_log_every_ticks", "max_horizen", "log_path",
}


@app.on_event("startup")
def startup() -> None:
    db.init_schema()
    if auth.ensure_default_user():
        print(f"[web] tbl_user empty: default account created ({auth.DEFAULT_USER}/{auth.DEFAULT_PASSWORD})")


# ---- 공통 ----
def require_user(request: Request) -> str:
    user = auth.read_token(request.cookies.get("session"))
    if user is None:
        raise HTTPException(status_code=307, headers={"Location": "/login"})
    return user


def render(request: Request, name: str, user: str | None = None, **ctx) -> HTMLResponse:
    ctx.update(request=request, user=user, guard_pid=guardctl.pid(), db_path=str(db.DB_PATH),
               msg=request.query_params.get("msg"), err=request.query_params.get("err"))
    return templates.TemplateResponse(request, name, ctx)


def back(path: str, msg: str | None = None, err: str | None = None) -> RedirectResponse:
    q = f"?msg={quote(msg)}" if msg else f"?err={quote(err)}" if err else ""
    return RedirectResponse(path + q, status_code=303)


def reload_msg(prefix: str) -> RedirectResponse:
    """저장 뒤 guard에 SIGHUP. 성공이면 "저장되었습니다", 못 보냈으면 저장은 됐다는 것과 이유를 보여준다"""
    ok, text = guardctl.reload()
    return back(prefix, msg="저장되었습니다.") if ok else back(prefix, err="저장되었습니다. (" + text + ")")


# ---- 로그인 ----
@app.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return render(request, "login.html")


@app.post("/login")
def login(username: str = Form(...), password: str = Form(...)):
    if not auth.verify(username, password):
        return back("/login", err="아이디 또는 비밀번호가 틀림")
    resp = RedirectResponse("/settings", status_code=303)
    resp.set_cookie("session", auth.make_token(username), httponly=True, samesite="lax", max_age=auth.SESSION_TTL_S)
    return resp


@app.get("/logout")
def logout():
    resp = RedirectResponse("/login", status_code=303)
    resp.delete_cookie("session")
    return resp


@app.get("/")
def index():
    return RedirectResponse("/settings", status_code=303)


# ---- 설정 ----
@app.get("/settings", response_class=HTMLResponse)
def settings_page(request: Request, user: str = Depends(require_user)):
    with db.connect() as con:
        if not db.table_exists(con, "tbl_config_info"):
            return render(request, "settings.html", user, groups=None)
        cols = [c for c in db.columns(con, "tbl_config_info") if c["name"] not in ("id", "updated_at") and c["name"] not in HIDDEN]
        row = con.execute("SELECT * FROM tbl_config_info WHERE id=1").fetchone()
        updated = con.execute("SELECT datetime(updated_at,'unixepoch','localtime') FROM tbl_config_info WHERE id=1").fetchone()
    rows = {c["name"]: {"name": c["name"], "type": c["type"], "value": row[c["name"]] if row else "",
                        "help": SETTING_HELP.get(c["name"], ""), "restart": c["name"] in RESTART_ONLY} for c in cols}
    groups = []
    for title, names in SETTING_GROUPS:
        items = [rows.pop(n) for n in names if n in rows]
        if items:
            groups.append((title, items))
    if rows:
        groups.append(("기타", list(rows.values())))
    return render(request, "settings.html", user, groups=groups, updated=updated[0] if updated else None)


@app.post("/settings")
async def settings_save(request: Request, user: str = Depends(require_user)):
    form = await request.form()
    with db.connect() as con:
        cols = [c for c in db.columns(con, "tbl_config_info") if c["name"] not in ("id", "updated_at") and c["name"] not in HIDDEN]
        sets, vals = [], []
        for c in cols:
            if c["name"] not in form:
                continue
            raw = str(form[c["name"]]).strip()
            if c["type"].upper() == "INTEGER":
                try:
                    vals.append(int(raw))
                except ValueError:
                    return back("/settings", err=f"{c['name']}: 정수가 아님 '{raw}'")
            else:
                vals.append(raw)
            sets.append(f"{c['name']}=?")
        if not sets:
            return back("/settings", err="바꿀 값이 없음")
        con.execute(f"UPDATE tbl_config_info SET {', '.join(sets)}, updated_at=strftime('%s','now') WHERE id=1", vals)
    return reload_msg("/settings")


# ---- 화이트리스트 ----
@app.get("/whitelist", response_class=HTMLResponse)
def whitelist_page(request: Request, user: str = Depends(require_user)):
    with db.connect() as con:
        rows = con.execute("SELECT id, ip, mask, note, datetime(created_at,'unixepoch','localtime') AS created_at"
                           " FROM tbl_whitelist ORDER BY id").fetchall() if db.table_exists(con, "tbl_whitelist") else []
    return render(request, "whitelist.html", user, rows=rows)


@app.post("/whitelist/add")
def whitelist_add(ip: str = Form(...), mask: str = Form(""), note: str = Form(""), user: str = Depends(require_user)):
    import ipaddress
    try:
        ipaddress.IPv4Address(ip.strip())
        if mask.strip():
            ipaddress.IPv4Address(mask.strip())
    except ValueError:
        return back("/whitelist", err="IP/마스크 형식이 틀림")
    with db.connect() as con:
        con.execute("INSERT INTO tbl_whitelist (ip, mask, note) VALUES (?, ?, ?)",
                    (ip.strip(), mask.strip() or None, note.strip() or None))
    return reload_msg("/whitelist")


@app.post("/whitelist/delete")
def whitelist_delete(id: int = Form(...), user: str = Depends(require_user)):
    with db.connect() as con:
        con.execute("DELETE FROM tbl_whitelist WHERE id=?", (id,))
    return reload_msg("/whitelist")


# ---- 차단 기록 ----
@app.get("/blocks", response_class=HTMLResponse)
def blocks_page(request: Request, user: str = Depends(require_user)):
    with db.connect() as con:
        rows = con.execute("SELECT datetime(time,'unixepoch','localtime') AS t, ip, reason FROM tbl_block ORDER BY id DESC LIMIT 200"
                           ).fetchall() if db.table_exists(con, "tbl_block") else []
    return render(request, "blocks.html", user, rows=rows)


# ---- 장비 ----
@app.get("/devices", response_class=HTMLResponse)
def devices_page(request: Request, user: str = Depends(require_user)):
    with db.connect() as con:
        devices = con.execute("SELECT mac, ip, name, note, datetime(first_seen,'unixepoch','localtime') AS first_seen,"
                              " datetime(last_seen,'unixepoch','localtime') AS last_seen FROM tbl_device ORDER BY last_seen DESC"
                              ).fetchall() if db.table_exists(con, "tbl_device") else []
        events = con.execute("SELECT datetime(time,'unixepoch','localtime') AS t, type, ip, old_mac, new_mac"
                             " FROM tbl_device_event ORDER BY id DESC LIMIT 100"
                             ).fetchall() if db.table_exists(con, "tbl_device_event") else []
    return render(request, "devices.html", user, devices=devices, events=events)


@app.post("/devices/name")
def devices_name(mac: str = Form(...), name: str = Form(""), note: str = Form(""), user: str = Depends(require_user)):
    with db.connect() as con:
        con.execute("UPDATE tbl_device SET name=?, note=? WHERE mac=?", (name.strip() or None, note.strip() or None, mac))
    return back("/devices", msg="저장되었습니다.")


@app.post("/devices/delete")
def devices_delete(mac: str = Form(...), user: str = Depends(require_user)):
    with db.connect() as con:
        con.execute("DELETE FROM tbl_device WHERE mac=?", (mac,))
    return back("/devices", msg="저장되었습니다.")


# ---- 계정 ----
@app.get("/account", response_class=HTMLResponse)
def account_page(request: Request, user: str = Depends(require_user)):
    return render(request, "account.html", user, info=auth.user_info(user))


@app.post("/account/password")
def account_password(current: str = Form(...), new: str = Form(...), confirm: str = Form(...), user: str = Depends(require_user)):
    if not auth.verify(user, current):
        return back("/account", err="현재 비밀번호가 틀림")
    if len(new) < 4 or new != confirm:
        return back("/account", err="새 비밀번호가 짧거나 확인과 다름")
    auth.change_password(user, new)
    return back("/account", msg="저장되었습니다.")
