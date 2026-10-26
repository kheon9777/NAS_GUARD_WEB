# NAS_GUARD_WEB

`guard`(../NAS_GUARD) 데몬의 웹 콘솔. guard와 같은 `guard.db`를 읽고 쓰며, 설정과 화이트리스트를 바꾸면 `sudo systemctl reload guard`(ExecReload가 SIGHUP)로 바로 반영함. (FastAPI + Jinja2)

## 실행화면
<img width="2553" height="1312" alt="image" src="https://github.com/user-attachments/assets/44d9e325-3c3f-4462-86ef-ac6fdb6f3cdc" />

<img width="2299" height="708" alt="image" src="https://github.com/user-attachments/assets/866716d2-15c1-44f7-ba93-ffb70f28737c" />

<img width="2538" height="783" alt="image" src="https://github.com/user-attachments/assets/bc371115-4853-4e1e-b2c7-1d8a6c4d4eb4" />
공유기에 syn플로드 방지를 풀었더니 실제로 누군가가 접속시도를 했다

## 구조

```
app/
  __init__.py     패키지 표시 (비어 있음)
  __main__.py     진입점. python -m app -> uvicorn 실행
  config.py       config.ini 읽기 (호스트, 포트, DB 경로)
  db.py           SQLite 연결. 웹 전용 테이블(tbl_user, tbl_web_config) 생성
  auth.py         계정과 세션. PBKDF2 비밀번호, HMAC 서명 쿠키
  guardctl.py     guard 프로세스 확인과 리로드 (sudo systemctl reload guard)
  main.py         라우트와 화면 로직
  views/          Jinja2 템플릿 (base, login, settings, whitelist, blocks, devices, account)
deploy/
  guard_web.service   systemd 유닛 (User=guardweb, Group=guard)
  guard_web.sudoers   guardweb에게 systemctl reload guard 만 허용. /etc/sudoers.d/guard_web
  config.ini          서비스용 설정 (DB 경로가 sv/guard/data/guard.db)
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
서비스는 로그인 불가 전용 계정 `guardweb`(그룹 `guard`)으로 돈다. 개발은 그냥 `./run.sh`.
- `guard.db` 쓰기: guard 쪽 `deploy.sh`가 `sv/guard/data/`를 root:guard 2770, DB 파일을 660으로 둔다. guardweb은 그룹 guard라 읽고 쓸 수 있고, WAL의 `-wal`, `-shm`을 새로 만들거나 지울 수도 있다. 실행 파일과 `logs/`는 root 소유 그대로.
- guard 리로드: `/etc/sudoers.d/guard_web`(`deploy/guard_web.sudoers`)이 guardweb에게 `/usr/bin/systemctl reload guard` 하나만 비밀번호 없이 허용한다. `guardctl.reload()`가 이 명령을 부른다. 다른 sudo는 안 된다.
- `/home/raspi`가 700이라 guardweb에게 지나가는(x) 권한만 ACL로 준다 (`setfacl -m u:guardweb:--x /home/raspi`, `deploy.sh install`).
- 전부 `./deploy.sh install`이 만든다 (그룹, 계정, ACL, sudoers, 유닛).
