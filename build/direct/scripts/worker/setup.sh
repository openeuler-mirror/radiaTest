#! /bin/sh

GIT_REPO=https://gitee.com/openeuler/radiaTest
PIP_REPO=https://pypi.tuna.tsinghua.edu.cn/simple

cd /opt || exit

dnf install -y git &&
    dnf install -y libvirt &&
    dnf install -y virt-install &&
    dnf install -y rsync &&
    dnf install -y python3-pip &&
    dnf install -y python3-devel

git clone "$GIT_REPO" ||
    git pull "$GIT_REPO" ||
    rm -rf ./radiaTest && git clone "$GIT_REPO" ||
    exit

cd /opt/radiaTest/radiaTest-worker/ || exit

mkdir /etc/radiaTest

cp -r ./conf/app/* /etc/radiaTest/ &&
    cp -r ./conf/supervisor/* /etc/ ||
    echo fail

mkdir log

pip3 install -r requirements.txt -i "$PIP_REPO" &&
    supervisord
