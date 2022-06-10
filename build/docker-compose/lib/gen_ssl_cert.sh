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

function gen_san_ext ()
{
    SAN=$1
    ipNum=1
    dnsNum=1
    while [[ $ipNum -gt 0 ]];do
        read -p "Setting alternative names, the type of this SAN is [DNS/IP]?(press ENTER to finish):" TYPE
        if [[ $TYPE == "IP" || $TYPE == "ip" ]];then
            read -p "Please Enter a valid public IP address IP.$ipNum = " IP
            SAN="${SAN}IP.${ipNum} = ${IP}\n"
            ipNum=$(($ipNum+1))
        elif [[ $TYPE == "DNS" || $TYPE == "dns" ]];then
            read -p "Please Enter a valid Domain name DNS.$dnsNum = " DNS
            SAN="${SAN}DNS.${dnsNum} = ${DNS}\n"
            dnsNum=$(($dnsNum+1))
        else
            break
        fi
    done

    if [[ $ipNum -eq 1 && $dnsNum -eq 1 ]];then
        echo "ERROR"
    else
        echo $SAN
    fi
}

function gen_ca_key ()
{
    echo "Create ca private key..."
    openssl genpkey -algorithm RSA -out private/cakey.pem -pkeyopt rsa_keygen_bits:2048
}

function gen_ca_cert ()
{
    echo "Create ca root certification..."
    openssl req -new -x509 -key private/cakey.pem -out cacert.pem -days 3650 -config conf/ca.cnf
    echo "ca root certification created success"
}

function gen_client_key ()
{
    echo "Create $1 private key..."
    openssl genpkey -algorithm RSA -out $1.key -pkeyopt rsa_keygen_bits:2048
}

function gen_client_csr ()
{
    echo "Create $1 certificate signing request..."
    SAN=`gen_san_ext "[ SubjectAlternativeName ]\n"`
    if [[ $SAN == "ERROR" ]];then
        echo "SubjectAlternativeName should not be empty, but no IP or DNS provided"
        exit 1
    fi

    openssl req -new -key $1.key -out csr/$1.csr -config <(cat conf/client.cnf <(echo -e "$SAN"))

    if [[ $1 == "server" ]];then
        gen_server_cert "$SAN"
    elif [[ $1 == "messenger" ]];then
        gen_messenger_cert "$SAN"
    else
        echo "Unsupported service to generate certfile"
        exit 1
    fi
}

function gen_server_cert ()
{
    echo "Self-sign Certification for server..."

    openssl ca \
        -in csr/server.csr -out certs/server.crt \
        -extensions v3_req \
        -config <(cat conf/ca.cnf <(printf "$1"))

    echo "Signature Success"
}

function gen_messenger_cert ()
{
    echo "Upload CSR to CA server..."
    read -p "Please type in the server address, [ ip:port | domain ]:" SERVER_ADDR
    read -p "If the server service works as selfsigned certifi, type in the path to the self-CA (press ENTER if not):" CACERT_PATH
    read -p "Please type in the messenger ip adress (public):" IPADDR
    
    if [ ! -n "$CACERT_PATH" ];then
        echo "request certification from server"
        curl -o 'certs/messenger.crt' \
            -H 'Content-Type: multipart/form-data' \
            -X POST 'https://'$SERVER_ADDR'/api/v1/ca-cert' \
            -F 'csr=@"csr/messenger.csr"' \
            -F 'ip='$IPADDR''  \
            -F san="$1"
    else
        echo "request certification from server, with self-signed root CA"
        curl -o 'certs/messenger.crt' \
            -H 'Content-Type: multipart/form-data' \
            -X POST 'https://'$SERVER_ADDR'/api/v1/ca-cert' \
            -F 'csr=@"csr/messenger.csr"' \
            -F 'ip='$IPADDR''  \
            -F san="$1" \
            --cacert $CACERT_PATH
    fi

    if [ -e $(cat certs/messenger.crt | grep Certificate) ];then
        echo -e "fail to ask server to sign for this CSR:\n$(cat certs/messenger.crt)"
        now=$(date "+%Y%m%d%H%M%S")
        mv certs/messenger.crt fail/$now.csr.error.log
        exit 1
    else
        echo "Signature Success"
    fi
}