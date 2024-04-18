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

FROM radia-test/gunicorn
LABEL maintainer="ethanzhang55@outlook.com"

RUN echo "umask 027" >> ~/.bashrc

RUN sed -i 's/^PermitRootLogin.*/PermitRootLogin no/' /etc/ssh/sshd_config

USER radiaTest

CMD celery -A manage.my_celery worker --loglevel=info --hostname=celery_openqa_reader@%h --queues=queue_read_openqa_group_overview,queue_read_openqa_tests_overview --pool=gevent -O fair
