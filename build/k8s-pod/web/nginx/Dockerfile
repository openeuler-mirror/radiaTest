FROM openeuler/openeuler:22.03-lts
LABEL maintainer="ethanzhang55@outlook.com"

ENV GIT_REPO https://gitee.com/openeuler/radiaTest

WORKDIR /opt

RUN dnf install -y git \
    && git clone $GIT_REPO \
    && dnf install -y nginx \
    && dnf install -y wget \
    && dnf install -y tar \
    && dnf install -y xz

WORKDIR /opt/radiaTest

RUN bash ./build/k8s-pod/web/nginx/install_nodejs.sh

WORKDIR /opt/radiaTest/radiaTest-web

RUN npm install --force \
    && cat ./deploy/nginx.conf > /etc/nginx/nginx.conf

CMD npm run build \
    && nginx