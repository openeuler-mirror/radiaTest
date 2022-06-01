# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  : Ethan-Zhang
# @email   : ethanzhang55@outlook.com
# @Date    : 2022/05/09 19:59:00
# @License : Mulan PSL v2
#####################################

#! /bin/sh

source "${OET_PATH}/lib/gen_ssl_cert.sh"

bash ./install_nodejs.sh || exit 1

if [[ -d "${OET_PATH}/../../radiaTest-web" ]]; then
    cd "${OET_PATH}/../../radiaTest-web"
else
    echo "lack of radiaTest-web, please update radiaTest"
    exit 1
fi

"$PKG_MNG" install -y git && \
    "$PKG_MNG" install -y nginx \
    "$PKG_MNG" install -y openssl

mkdir /usr/share/radiaTest

npm install --force \
    && npm run build

mkdir /etc/radiaTest/server_nginx

cp -r /etc/nginx/* /etc/radiaTest/server_nginx/ \
    && cat ./deploy/nginx.conf > /etc/radiaTest/server_nginx/nginx.conf \
    && cp -r ./deploy/conf.d/* /etc/radiaTest/server_nginx/conf.d/

echo "start to generate SSL certification for nginx of server"
mkdir -p /etc/radiaTest/server_ssl/certs
cd /etc/radiaTest/server_ssl/

if [[ ! -f "./selfsigned.key" && ! -f "./certs/selfsigned.crt" ]];then
    gen_ssl_cert server
else
    echo "SSL Crt&Key already exist, please make sure they are validation. Otherwise, the service could not work normally."
fi