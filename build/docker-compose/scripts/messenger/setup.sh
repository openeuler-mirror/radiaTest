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

cp ./deploy/* /etc/radiaTest/messenger_nginx/

echo "start to generate SSL certification for messenger"
mkdir -p /etc/radiaTest/messenger_ssl/certs
cd /etc/radiaTest/messenger_ssl/

if [[ ! -f "./messenger.key" && ! -f "./certs/messenger.crt" ]];then
    gen_ssl_cert messenger
else
    echo "SSL Crt&Key already exist, please make sure their validation. Otherwise, the services could not work normally."
fi

