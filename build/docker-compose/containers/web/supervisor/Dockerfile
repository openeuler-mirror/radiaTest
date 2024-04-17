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

FROM openeuler/openeuler:22.03-lts
LABEL maintainer="ethanzhang55@outlook.com"

WORKDIR /opt/

ENV TZ Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ENV GIT_REPO https://gitee.com/openeuler/radiaTest
ENV PIP_REPO https://pypi.tuna.tsinghua.edu.cn/simple

RUN dnf install -y git \
    && git clone $GIT_REPO \
    && dnf install -y make \
    && dnf install -y rsync \
    && dnf install -y openssl \
    && dnf install -y expect \
    && dnf install -y iputils \
    && dnf install -y cronie \
    && dnf install -y logrotate \
    && dnf install -y python3-pip \
    && dnf install -y python3-devel \
    && dnf install -y sudo \
    && dnf install -y shadow

WORKDIR /opt/radiaTest/radiaTest-server/

COPY ./logrotate /etc/logrotate.d/supervisor

RUN crond \
    && echo "* 1 * * * root run-parts /etc/cron.daily" >> /etc/crontab \
    && crontab /etc/crontab

RUN cp -r ./conf/supervisor/* /etc/

RUN bash ./install_rar.sh

# 增加radiaTest、 uncompress(文件解压专用)
RUN useradd -ms /bin/bash radiaTest
RUN useradd -ms /bin/bash uncompress
# 配置radiaTest免密操作uncompress
RUN echo "radiatest ALL=(uncompress) NOPASSWD: ALL" >> /etc/sudoers

# 创建文件存放目录
RUN mkdir -p /opt/radiaTest/tmp/export
RUN mkdir -p /opt/radiaTest/tmp/testcase

# /opt/radiaTest增加权限
RUN chown -R radiaTest:radiaTest /opt/radiaTest
RUN chown -R radiaTest:radiaTest /etc/supervisord.d
RUN chown -R radiaTest:radiaTest /etc/supervisord.conf

RUN chmod -R 755 /opt/radiaTest
RUN mkdir /etc/radiaTest
RUN chmod -R 740 /etc/radiaTest

# uncompress用户解压需要rarfile库
RUN sudo -u uncompress pip3 install rarfile==4.0

# 授予启动supervisord的相应用户的权限
RUN chmod 777 /run
USER radiaTest
ENV PATH="/home/radiaTest/.local/bin:${PATH}"
RUN pip3 install -r requirements.txt -i $PIP_REPO

CMD bash /opt/radiaTest/build/docker-compose/containers/web/supervisor/init_db.sh \
    && supervisord -n
