"""guard 프로세스 상태 확인과 SIGHUP(리로드) 전송. 웹은 root로 돌므로(__main__에서 확인) 시그널을 바로 보낸다."""
import os
import signal
import subprocess


def pid() -> int | None:
    try:
        out = subprocess.run(["pgrep", "-x", "guard"], capture_output=True, text=True, timeout=3).stdout.split()
    except Exception:
        return None
    return int(out[0]) if out else None


def reload() -> tuple[bool, str]:
    """설정, 화이트리스트를 다시 읽게 한다. 반환 (성공, 메시지)."""
    p = pid()
    if p is None:
        return False, "현재 서비스가 실행중이지 않습니다."
    try:
        os.kill(p, signal.SIGHUP)
        return True, f"guard(pid {p})에 SIGHUP 전송"
    except OSError as e:
        return False, f"서비스에 반영하지 못했습니다. ({e})"
