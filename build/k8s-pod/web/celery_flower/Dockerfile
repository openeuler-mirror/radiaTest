FROM openeuler/openeuler:22.03-lts

LABEL maintainer="Ethan-Zhang<ethanzhang55@outlook.com>"

ENV TZ Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /opt

RUN dnf install -y python3-pip && \
    dnf install -y python3-devel

RUN pip3 install celery==5.1.2 && \
    pip3 install flower==1.0.0

ENV LISTEN 5555

EXPOSE ${LISTEN}

ENV AMQP_USER radiaTest
ENV AMQP_PASSWD 1234
ENV AMQP_HOST localhost
ENV AMQP_PORT 5672

CMD celery flower --address=0.0.0.0 --port=${LISTEN} --broker=amqp://${AMQP_USER}:${AMQP_PASSWD}@${AMQP_HOST}:${AMQP_PORT}/radiaTest