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
# @Date    : 2022/05/26 19:59:00
# @License : Mulan PSL v2
#####################################

#! /bin/sh

source "${OET_PATH}/lib/gen_ssl_cert.sh"

if [[ -d "${OET_PATH}/../../radiaTest-messenger" ]]; then
    cd "${OET_PATH}/../../radiaTest-messenger"
else
    echo "lack of radiaTest-messenger, please update radiaTest"
    exit 1
fi

"$PKG_MNG" install -y nginx && \
    "$PKG_MNG" install -y openssl

mkdir /etc/radiaTest/messenger_nginx

cp -r ./conf/nginx/* /etc/radiaTest/messenger_nginx/

mkdir -p /etc/radiaTest/messenger_ssl/certs
mkdir -p /etc/radiaTest/messenger_ssl/conf
mkdir -p /etc/radiaTest/messenger_ssl/csr
mkdir -p /etc/radiaTest/messenger_ssl/fail

cd /etc/radiaTest/messenger_ssl/
cat ${OET_PATH}/conf/client_openssl.cnf > conf/client.cnf


if [[ ! -f "messenger.key" ]];then
    gen_client_key "messenger"
fi

if [[ ! -f "csr/messenger.csr" && ! -f "certs/messenger.crt" ]];then
    gen_client_csr "messenger"
elif [[ ! -f "certs/messenger.crt" ]];then
    echo "Using exist CSR: messenger.csr to ask CA Signature"
    SAN=`gen_san_ext "[ SubjectAlternativeName ]\n"`
    gen_messenger_cert "$SAN"
else
    echo "SSL CSR/CRT files already exist, please make sure their validation. Otherwise, the services could not work normally."
fi
