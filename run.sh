#!/bin/sh
# guard 웹 콘솔 실행. 포트와 DB 경로는 config.ini.
# 처음이면: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
# root가 아니면 바로 종료한다 (guard.db 쓰기, guard에 HUP 전송). sudo ./run.sh 로 띄운다. 서비스도 root로 돈다
cd "$(dirname "$0")" || exit 1
exec .venv/bin/python -m app
