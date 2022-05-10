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

FROM openeuler/openeuler:22.03-lts
LABEL maintainer="ethanzhang55@outlook.com"

ENV username radiaTest
ENV password 1234

WORKDIR /opt/

ENV GIT_REPO https://gitee.com/openeuler/radiaTest
ENV PIP_REPO https://pypi.tuna.tsinghua.edu.cn/simple

RUN dnf install -y git \
    && git clone $GIT_REPO \
    && dnf install -y make \
    && dnf install -y rsync \
    && dnf install -y logrotate \
    && dnf install -y python3-pip \
    && dnf install -y python3-devel

WORKDIR /opt/radiaTest/radiaTest-server/

COPY ./logrotate /etc/logrotate.d/supervisor

RUN logrotate /etc/logrotate.d/supervisor

RUN cp -r ./conf/supervisor/* /etc/

RUN bash ./install_rar.sh \
    && pip3 install -r requirements.txt -i $PIP_REPO

CMD bash /opt/radiaTest/build/k8s-pod/web/supervisor/init_db.sh \
    && supervisord -n
