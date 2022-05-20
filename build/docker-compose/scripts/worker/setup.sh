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
# @Date    : 2022/05/06 14:13:00
# @License : Mulan PSL v2
#####################################

#! /bin/sh

"$PKG_MNG" install -y git &&
    "$PKG_MNG" install -y libvirt &&
    "$PKG_MNG" install -y virt-install &&
    "$PKG_MNG" install -y rsync &&
    "$PKG_MNG" install -y cronie &&
    "$PKG_MNG" install -y logrotate &&
    "$PKG_MNG" install -y python3-pip &&
    "$PKG_MNG" install -y python3-devel

if [[ -d "${OET_PATH}/../../radiaTest-worker" ]]; then
    cd "${OET_PATH}/../../radiaTest-worker"
else
    echo "lack of radiaTest-worker, please update radiaTest"
    exit 1
fi

echo "* 1 * * * root run-parts /etc/cron.daily" >> /etc/crontab \
    && crontab /etc/crontab

mkdir /etc/radiaTest

cp -r ./conf/supervisor/* /etc/ || exit 1

pip3 install -r requirements.txt -i "$PIP_REPO" &&
    supervisord
