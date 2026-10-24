"""python -m app : config.ini의 host/port로 uvicorn 실행. 일반 계정(raspi)으로 돈다."""
import uvicorn

from .config import HOST, PORT

uvicorn.run("app.main:app", host=HOST, port=PORT)
