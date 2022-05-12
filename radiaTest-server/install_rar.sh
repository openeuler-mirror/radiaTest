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

# /bin/sh

basearch=$(uname -m)

if [[ "${basearch}" == "x86_64" || "${basearch}" == "aarch64" ]];then
    basearch="x64"
else
    echo "Error: Unsupported Arch"
    exit 1
fi

RAR=$(which unrar 2>/dev/null)

if [ ! -z "${RAR}" ]; then
    exit 0
fi

dnf install -y wget

wget https://www.rarlab.com/rar/rarlinux-${basearch}-612.tar.gz \
    && tar -xzf rarlinux-x64-612.tar.gz \
    && cd rar \
    && make \
    && make install

RAR=$(which unrar 2>/dev/null)

if [ -z "${RAR}" ]; then
    exit 1
else
    cd ../ \
    && rm -rf rar/ \
    && rm rarlinux-x64-612.tar.gz
fi
