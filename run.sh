#!/bin/sh
# guard 웹 콘솔 실행. 포트와 DB 경로는 config.ini.
# 처음이면: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
# 일반 계정으로 돈다. guard.db는 raspi 소유여야 하고(sudo chown raspi guard.db*), 리로드는 sudo systemctl reload guard
cd "$(dirname "$0")" || exit 1
exec .venv/bin/python -m app
