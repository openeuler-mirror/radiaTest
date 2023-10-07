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
# @Date    : 2022/06/16 10:17:00
# @License : Mulan PSL v2
#####################################
#!/bin/bash -c

mkdir -p /etc/radiaTest_ssl
pushd /etc/radiaTest_ssl || exit

mkdir conf certs newcerts crl csr private  

if [[ ! -f "conf/ca.cnf" ]];then
    cat /opt/radiaTest/build/k8s-pod/web/gunicorn/ca_openssl.cnf > conf/ca.cnf
fi

if [[ ! -f "index.txt" ]];then
    touch index.txt
    echo 01 > serial
fi

if [[ ! -f "private/cakey.pem" ]];then
    openssl genpkey -algorithm RSA -out private/cakey.pem -pkeyopt rsa_keygen_bits:2048
fi

if [[ ! -f "cacert.pem" ]];then
    openssl req -new -x509 \
        -key private/cakey.pem \
        -out cacert.pem \
        -days 3650 \
        -subj "/C=CN/ST=Zhejiang/L=Hangzhou/O=openEuler/OU=QA-sig/CN=radiatest.openeuler.org" \
        -config conf/ca.cnf
fi

popd || exit
