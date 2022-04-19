#! /bin/sh

GIT_REPO=https://gitee.com/openeuler/radiaTest

bash ./install_nodejs.sh

cd /tmp/ || exit

dnf install -y git &&
    dnf install -y nginx

git clone "$GIT_REPO" ||
    git pull "$GIT_REPO" ||
    rm -rf ./radiaTest && git clone "$GIT_REPO" ||
    exit

cd /tmp/radiaTest/radiaTest-web/ || exit

mkdir /usr/share/radiaTest

npm install --force \
    && npm run build \
    && cat ./deploy/nginx.conf >/etc/nginx/nginx.conf \
    && cp -r ./dist /usr/share/radiaTest/
