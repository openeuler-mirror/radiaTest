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

USER radiaTest

CMD celery -A manage.my_celery worker --loglevel=info --hostname=celery_periodic_worker --queues=queue_update_celerytask_status,queue_read_openqa_homepage,queue_update_issue_type_state,queue_update_all_issue_rate,queue_update_all_task_progress --pool=gevent --concurrency=40
