#!/bin/sh
#   ./deploy.sh : app/ + requirements.txt 복사, 의존성 설치, 재시작
#   ./deploy.sh install : 처음 한 번, venv 생성 + 유닛 파일, sudoers 등록 + enable + 배포
# 서비스는 raspi로 돌므로 $SV 아래는 전부 raspi 소유로 둔다 (예전에 root로 복사한 파일이 있으면 chown)
set -e
cd "$(dirname "$0")"
SV=/home/raspi/sv/guard_web   # 서비스 경로
GUARD_DB=/home/raspi/sv/guard/guard.db   # guard와 같이 쓰는 DB. 웹이 쓰려면 raspi 소유여야 함
WHAT=${1:-deploy}

deploy_web() {
    sudo chown -R raspi:raspi $SV
    rm -rf $SV/app
    cp -r app $SV/app
    rm -rf $SV/app/__pycache__ $SV/app/*/__pycache__
    cp requirements.txt $SV/
    $SV/.venv/bin/pip install -q -r $SV/requirements.txt	# 의존성이 바뀌었을 때 반영
    [ -f $SV/config.ini ] || cp deploy/config.ini $SV/config.ini	# 설정은 처음에만 (운영 설정이 들어 있음)
    # guard(root)가 raspi 소유 DB를 열면 -wal, -shm도 raspi 소유로 만들어지므로 chown 한 번이면 됨
    [ -f $GUARD_DB ] && sudo chown raspi:raspi $GUARD_DB $GUARD_DB-wal $GUARD_DB-shm 2>/dev/null || true
    sudo systemctl restart guard_web
    echo "guard_web: $(systemctl is-active guard_web)"
}

install_unit() {
    mkdir -p $SV
    [ -d $SV/.venv ] || python3 -m venv $SV/.venv
    sudo cp deploy/guard_web.service /etc/systemd/system/
    sudo install -m 440 -o root -g root deploy/guard_web.sudoers /etc/sudoers.d/guard_web
    sudo visudo -c -f /etc/sudoers.d/guard_web	# 문법이 틀리면 sudo 전체가 막히므로 반드시 검사
    sudo systemctl daemon-reload
    sudo systemctl enable guard_web
}

case "$WHAT" in
    deploy) deploy_web ;;
    install) install_unit; deploy_web ;;
    *) echo "usage: $0 [deploy|install]"; exit 1 ;;
esac
