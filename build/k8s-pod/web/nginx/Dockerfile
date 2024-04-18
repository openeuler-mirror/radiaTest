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

ENV TZ Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

ENV GIT_REPO https://gitee.com/openeuler/radiaTest
ENV BRANCH master

WORKDIR /opt

RUN dnf install -y git \
    && git clone -b $BRANCH $GIT_REPO \
    && dnf install -y nginx \
    && dnf install -y wget \
    && dnf install -y tar \
    && dnf install -y xz \
    && dnf install -y shadow

WORKDIR /opt/radiaTest

RUN bash ./build/k8s-pod/web/nginx/install_nodejs.sh

WORKDIR /opt/radiaTest/radiaTest-web

# 创建radiaTest用户
RUN useradd -ms /bin/bash radiaTest
# 增加权限
RUN mkdir -p /opt/radiaTest/radiaTest-web/nginx_log
RUN chown -R radiaTest:radiaTest /opt/radiaTest
RUN chown -R radiaTest:radiaTest /usr/share/nginx
RUN chown -R radiaTest:radiaTest /var/lib/nginx
RUN chown -R radiaTest:radiaTest /var/log/nginx
RUN chmod -R 740 /opt/radiaTest
RUN \cp ./deploy/nginx.conf ./deploy/server.conf /etc/nginx/
RUN chown -R radiaTest:radiaTest /etc/nginx

RUN echo "umask 027" >> ~/.bashrc

RUN sed -i 's/^PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config

USER radiaTest
RUN npm cache clean --force \
    && npm install --force --registry=https://registry.npmmirror.com \
    && npm run build

ENTRYPOINT [ "nginx", "-c", "/etc/nginx/nginx.conf", "-g", "daemon off;" ]
