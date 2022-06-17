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

"$PKG_MNG" install -y git \
    && "$PKG_MNG" install -y nginx \
    && "$PKG_MNG" install -y openssl

mkdir /usr/share/radiaTest

npm install --force \
    && npm run build || exit 1

mkdir /etc/radiaTest/server_nginx

cp -r ./deploy/* /etc/radiaTest/server_nginx/

mkdir -p /etc/radiaTest/server_ssl/certs
mkdir -p /etc/radiaTest/server_ssl/csr
mkdir -p /etc/radiaTest/server_ssl/crl
mkdir -p /etc/radiaTest/server_ssl/newcerts
mkdir -p /etc/radiaTest/server_ssl/private
mkdir -p /etc/radiaTest/server_ssl/conf

cd /etc/radiaTest/server_ssl/
cat ${OET_PATH}/conf/ca_openssl.cnf > conf/ca.cnf
cat ${OET_PATH}/conf/client_openssl.cnf > conf/client.cnf

if [[ ! -f "index.txt" ]];then
    touch index.txt
fi
if [[ ! -f "serial" ]];then
    echo 01 > ./serial
fi

if [[ ! -f "./private/cakey.pem" ]];then
    gen_ca_key
fi

if [[ ! -f "./cacert.pem" ]];then
    gen_ca_cert
fi

if [[ ! -f "server.key" ]];then
    gen_client_key "server"
fi

if [[ ! -f "csr/server.csr" && ! -f "certs/server.crt" ]];then
    gen_client_csr "server"
elif [[ ! -f "certs/server.crt" ]];then
    echo "Using exist CSR: server.csr to ask CA Signature"
    SAN=`gen_san_ext "[ SubjectAlternativeName ]\n"`
    gen_server_cert "$SAN"
else
    echo "SSL Certfile already exist, please make sure they are validation. Otherwise, the service could not work normally."
fi