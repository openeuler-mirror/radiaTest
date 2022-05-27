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
# @Date    : 2022/05/27 19:59:00
# @License : Mulan PSL v2
#####################################

#! /bin/sh

function gen_ssl_cert ()
{
    echo "REMINDING: the common name should be set as the real public server name (server ip/domain name/host name)"

    read -p "Setting alternative names (domains or ips):" DOMAIN

    echo "Create server key..."

    openssl genpkey -algorithm RSA -out selfsigned.key -pkeyopt rsa_keygen_bits:2048

    echo "Create server certificate signing request..."

    SUBJECT="/C=CN/ST=Zhejiang/L=Hangzhou/O=openEuler/OU=QA/CN=$DOMAIN"

    openssl req -new -key selfsigned.key -out selfsigned.csr -subj $SUBJECT

    echo "Sign SSL certificate..."

    echo "Gen subject ext file..."

    echo "keyUsage = nonRepudiation, digitalSignature, keyEncipherment
    extendedKeyUsage = serverAuth, clientAuth
    subjectAltName=@SubjectAlternativeName

    [ SubjectAlternativeName ]
    IP.1 = $DOMAIN" > ./selfsigned.ext

    openssl x509 -req -days 3650 -in selfsigned.csr -signkey selfsigned.key -out ./certs/selfsigned.crt -extfile selfsigned.ext
}