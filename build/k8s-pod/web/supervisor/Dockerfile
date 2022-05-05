FROM openeuler/openeuler:22.03-lts
LABEL maintainer="ethanzhang55@outlook.com"

ENV username radiaTest
ENV password 1234

WORKDIR /opt/

ENV GIT_REPO https://gitee.com/openeuler/radiaTest
ENV PIP_REPO https://pypi.tuna.tsinghua.edu.cn/simple

RUN dnf install -y git \
    && git clone $GIT_REPO \
    && dnf install -y rsync \
    && dnf install -y logrotate \
    && dnf install -y python3-pip \
    && dnf install -y python3-devel

WORKDIR /opt/radiaTest/radiaTest-server/

COPY ./logrotate /etc/logrotate.d/supervisor

RUN logrotate /etc/logrotate.d/supervisor

RUN cp -r ./conf/supervisor/* /etc/

RUN pip3 install -r requirements.txt -i $PIP_REPO

CMD bash /opt/radiaTest/build/k8s-pod/web/supervisor/init_db.sh \
    && supervisord -n
