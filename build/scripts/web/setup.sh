#! /bin/sh

GIT_REPO=https://gitee.com/openeuler/radiaTest

cd /tmp/ || exit

dnf install -y git &&
    dnf install -y nginx &&
    dnf install -y nodejs
# 后续采用单独wget node-v14.17的二进制包

git clone "$GIT_REPO" ||
    git pull "$GIT_REPO" ||
    rm -rf ./radiaTest && git clone "$GIT_REPO" ||
    exit

cd /tmp/radiaTest/radiaTest-web/ || exit

npm install && npm run build &&
    cat ./deploy/nginx.conf >/etc/nginx/nginx.conf &&
    mkdir /usr/share/radiaTest &&
    cp -r ./dist /usr/share/radiaTest/
