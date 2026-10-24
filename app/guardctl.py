"""guard 프로세스 상태 확인과 리로드. 웹은 일반 계정으로 돌므로 시그널을 직접 보내지 않고
sudo systemctl reload guard 를 쓴다 (guard.service의 ExecReload가 SIGHUP. deploy/guard_web.sudoers 참고)."""
import subprocess

RELOAD_CMD = ["sudo", "-n", "/usr/bin/systemctl", "reload", "guard"]  # sudoers에 적힌 명령과 같아야 함


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
        r = subprocess.run(RELOAD_CMD, capture_output=True, text=True, timeout=10)
    except Exception as e:
        return False, f"서비스에 반영하지 못했습니다. ({e})"
    if r.returncode != 0:
        return False, f"서비스에 반영하지 못했습니다. ({r.stderr.strip() or 'systemctl reload 실패'})"
    return True, f"guard(pid {p}) reload"
