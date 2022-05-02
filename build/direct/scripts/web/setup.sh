#! /bin/sh

bash ./install_nodejs.sh || exit 1

if [[ -d "${OET_PATH}/../../radiaTest-web" ]]; then
    cd "${OET_PATH}/../../radiaTest-web"
else
    echo "lack of radiaTest-web, please update radiaTest"
    exit 1
fi

"$PKG_MNG" install -y git &&
    "$PKG_MNG" install -y nginx

mkdir /usr/share/radiaTest

npm install --force \
    && npm run build \
    && cat ./deploy/nginx.conf >/etc/nginx/nginx.conf \
    && cp -r ./dist /usr/share/radiaTest/
