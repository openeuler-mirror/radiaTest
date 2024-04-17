# Copyright (c) [2022] Huawei Technologies Co.,Ltd.ALL rights reserved.
# This program is licensed under Mulan PSL v2.
# You can use it according to the terms and conditions of the Mulan PSL v2.
#          http://license.coscl.org.cn/MulanPSL2
# THIS PROGRAM IS PROVIDED ON AN "AS IS" BASIS, WITHOUT WARRANTIES OF ANY KIND,
# EITHER EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO NON-INFRINGEMENT,
# MERCHANTABILITY OR FIT FOR A PARTICULAR PURPOSE.
# See the Mulan PSL v2 for more details.
####################################
# @Author  :
# @email   :
# @Date    : 2022/05/09 19:59:00
# @License : Mulan PSL v2
#####################################

#!/bin/bash -c

# define env variables
node_req_v="v16.14.2"
npm_req_v="8.5.0"
npx_req_v="8.5.0"
workdir="/usr/local/bin"
basearch=$(uname -m)
nodejs_version=$(node -v 2>/dev/null)

# check nodejs
if [[ -n "${nodejs_version}" && "${nodejs_version}" = "${node_req_v}" ]];then
    echo "nodejs ${node_req_v} has been prepared"
    exit 0
elif [[ -n "${nodejs_version}" ]]; then
    n=3
    while [ $n -ge 0 ];do

        read -p "nodejs ${nodejs_version} is not appropriate for radiaTest, ${node_req_v} is going to replace this version, [Y|N]?"
        if [[ "${REPLY}" != [YyNn] ]];then
            echo "you should enter Y/y or N/n"
        elif [[ "${REPLY}" == [Nn] ]];then
            exit 1
        else
            "$PKG_MNG" remove -y nodejs || ( echo "remove nodejs ${nodejs_version} failed" && exit 1 )
            echo "nodjs ${nodejs_version} has been removed"
            break
        fi

        if [ $n = 0 ];then
            exit 1
        fi

        let n--
    done
else
    n=3
    while [ $n -ge 0 ];do

        read -p "no nodejs installed, nodejs ${node_req_v} is going to be installed from https://nodejs.org, [Y|N]?"
        if [[ "${REPLY}" != [YyNn] ]];then
            echo "you should enter Y/y or N/n"
        elif [[ "${REPLY}" == [Nn] ]];then
            exit 1
        else
            break
        fi
        
        if [ $n = 0 ];then
            exit 1
        fi

        let n--
    done
fi

# prepare nodejs
cd "${workdir}"

if [ "${basearch}" = "x86_64" ];then
    basearch="x64"
elif [ "${basearch}" = "aarch64" ];then
    basearch="arm64"
else
    echo "Error: Unsupported Arch"
    exit 1
fi

"$PKG_MNG" install -y tar || exit 1

wget https://npmmirror.com/mirrors/node/"${node_req_v}"/node-"${node_req_v}"-linux-"${basearch}".tar.xz || exit 1 \
    && tar -xJf node-"${node_req_v}"-linux-"${basearch}".tar.xz || exit 1 \
    && rm -rf node-"${node_req_v}"-linux-"${basearch}".tar.xz || exit 1

ln -s "${workdir}"/node-"${node_req_v}"-linux-"${basearch}"/bin/node "${workdir}"/node
ln -s "${workdir}"/node-"${node_req_v}"-linux-"${basearch}"/bin/npm "${workdir}"/npm
ln -s "${workdir}"/node-"${node_req_v}"-linux-"${basearch}"/bin/npx "${workdir}"/npx

node=$(node -v)
npm=$(npm -v)
npx=$(npx -v)

# check version
if [[ "${node}" != "${node_req_v}" && "${npm}" != "${npm_req_v}" && "${npx}" != "${npx_req_v}" ]]; then
    echo "Internal Error: Install Nodejs ${node_req_v} Failed."
    echo "clean environment..."
    rm -rf "${workdir}"/node \
        && rm -rf "${workdir}"/npm \
        && rm -rf "${workdir}"/npx \
        && rm -rf "${workdir}"/node-"${node_req_v}"-linux-"${basearch}"
    exit 1
else
    echo "nodejs ${node_req_v} has been prepared"
fi
