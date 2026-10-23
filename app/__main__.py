"""python -m app : config.ini의 host/port로 uvicorn 실행. root가 아니면 바로 종료한다."""
import os
import sys

if os.geteuid() != 0:
    sys.exit("[web] root 권한이 필요합니다 (guard.db 쓰기, guard에 SIGHUP 전송). sudo ./run.sh 로 실행하세요.")

import uvicorn

from .config import HOST, PORT

uvicorn.run("app.main:app", host=HOST, port=PORT)
