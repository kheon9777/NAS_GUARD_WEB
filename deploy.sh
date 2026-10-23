#!/bin/sh
#   ./deploy.sh : app/ + requirements.txt 복사, 의존성 설치, 재시작
#   ./deploy.sh install : 처음 한 번, venv 생성 + 유닛 파일 등록 + enable + 배포
set -e
cd "$(dirname "$0")"
SV=/home/raspi/sv/guard_web   # 서비스 경로
WHAT=${1:-deploy}

deploy_web() {
    sudo rm -rf $SV/app
    sudo cp -r app $SV/app
    sudo rm -rf $SV/app/__pycache__ $SV/app/*/__pycache__
    sudo cp requirements.txt $SV/
    sudo $SV/.venv/bin/pip install -q -r $SV/requirements.txt	# 의존성이 바뀌었을 때 반영
    [ -f $SV/config.ini ] || sudo cp deploy/config.ini $SV/config.ini	# 설정은 처음에만 (운영 설정이 들어 있음)
    sudo systemctl restart guard_web
    echo "guard_web: $(systemctl is-active guard_web)"
}

install_unit() {
    sudo mkdir -p $SV
    [ -d $SV/.venv ] || sudo python3 -m venv $SV/.venv
    sudo cp deploy/guard_web.service /etc/systemd/system/
    sudo systemctl daemon-reload
    sudo systemctl enable guard_web
}

case "$WHAT" in
    deploy) deploy_web ;;
    install) install_unit; deploy_web ;;
    *) echo "usage: $0 [deploy|install]"; exit 1 ;;
esac
