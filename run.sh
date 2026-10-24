#!/bin/sh
# guard 웹 콘솔 개발 실행. 포트와 DB 경로는 config.ini (기본은 ../NAS_GUARD/guard.db).
# 처음이면: python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
# 서비스는 전용 계정 guardweb으로 돌지만 개발은 그냥 내 계정으로 띄운다. 리로드는 sudo systemctl reload guard
cd "$(dirname "$0")" || exit 1
exec .venv/bin/python -m app
