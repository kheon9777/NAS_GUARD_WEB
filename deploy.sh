#!/bin/sh
#   ./deploy.sh : app/ + requirements.txt 복사, 의존성 설치, 재시작
#   ./deploy.sh install : 처음 한 번, venv 생성 + 서비스 계정 + 유닛 파일, sudoers 등록 + enable + 배포
# 권한 구조: 서비스는 로그인 불가 계정 guardweb(그룹 guard)으로 돈다. 파일은 raspi 소유(읽기만 하면 됨),
# DB는 guard의 data/ (root:guard 2770, 660. ../NAS_GUARD/deploy.sh setup_data)를 그룹으로 쓰고,
# guard 리로드는 sudoers로 허용한 systemctl reload guard 하나뿐이다
set -e
cd "$(dirname "$0")"
SV=/home/raspi/sv/guard_web   # 서비스 경로
WEB_USER=guardweb
WHAT=${1:-deploy}

deploy_web() {
    sudo chown -R raspi:raspi $SV	# 예전에 root로 복사한 파일이 있으면 정리
    rm -rf $SV/app
    cp -r app $SV/app
    rm -rf $SV/app/__pycache__ $SV/app/*/__pycache__
    cp requirements.txt $SV/
    $SV/.venv/bin/pip install -q -r $SV/requirements.txt	# 의존성이 바뀌었을 때 반영
    [ -f $SV/config.ini ] || cp deploy/config.ini $SV/config.ini	# 설정은 처음에만 (운영 설정이 들어 있음)
    sudo systemctl restart guard_web
    echo "guard_web: $(systemctl is-active guard_web)"
}

install_unit() {
    mkdir -p $SV
    [ -d $SV/.venv ] || python3 -m venv $SV/.venv
    # 서비스 계정. 그룹 guard는 guard의 deploy.sh도 만들지만 설치 순서에 상관없도록 여기서도 만든다
    sudo groupadd -f guard
    getent passwd $WEB_USER >/dev/null || sudo useradd -r -g guard -s /usr/sbin/nologin -d /nonexistent $WEB_USER
    # /home/raspi 가 700이라 guardweb이 그 아래(sv/guard_web, sv/guard/data)로 들어가려면 지나가는(x) 권한만 ACL로 준다
    sudo setfacl -m u:$WEB_USER:--x /home/raspi
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
