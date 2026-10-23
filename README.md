# NAS_GUARD_WEB

`guard`(../NAS_GUARD) 데몬의 웹 콘솔. guard와 같은 `guard.db`를 읽고 쓰며, 설정과 화이트리스트를 바꾸면 guard에 SIGHUP을 보내 바로 반영함. (FastAPI + Jinja2)

## 구조

```
app/
  __init__.py     패키지 표시 (비어 있음)
  __main__.py     진입점. python -m app -> uvicorn 실행
  config.py       config.ini 읽기 (호스트, 포트, DB 경로)
  db.py           SQLite 연결. 웹 전용 테이블(tbl_user, tbl_web_config) 생성
  auth.py         계정과 세션. PBKDF2 비밀번호, HMAC 서명 쿠키
  guardctl.py     guard 프로세스 확인과 SIGHUP 전송
  main.py         라우트와 화면 로직
  views/          Jinja2 템플릿 (base, login, settings, whitelist, blocks, devices, account)
deploy/
  guard_web.service   systemd 유닛
  config.ini          서비스용 설정 (DB 경로가 sv/guard/guard.db)
config.ini        개발용 설정
run.sh            개발 실행 (.venv/bin/python -m app)
deploy.sh         서비스 배포
```

| 화면 | 하는 일 | guard 테이블 |
|---|---|---|
| `/settings` | 감지 임계치, 차단 시간, 장비 만료, 로그 보관 등. 저장하면 HUP | `tbl_config_info` |
| `/whitelist` | 감지, 차단 제외 IP 추가/삭제. HUP | `tbl_whitelist` |
| `/blocks` | 차단 기록 보기 | `tbl_block` |
| `/devices` | LAN 장비 목록, 이름 붙이기, 장비 이벤트 | `tbl_device`, `tbl_device_event` |
| `/account` | 관리자 비밀번호 변경 | `tbl_user` (웹 전용) |

설정 폼은 `tbl_config_info`의 컬럼을 읽어서 만들므로 guard에 설정이 추가되면 자동으로 표시됨

## 실행

```sh
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt   # 처음 한 번
./run.sh            # config.ini의 포트로
```

서비스 배포는 `./deploy.sh` (app 복사, pip install, `guard_web` 재시작). 처음 한 번은 `./deploy.sh install`. 운영 경로는 `/home/raspi/sv/guard_web`

## 권한
시작할 때 root가 아니면 안내를 찍고 바로 종료. 서비스는 `User=root`, 개발은 `sudo ./run.sh`
