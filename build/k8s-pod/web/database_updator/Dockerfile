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

FROM radia-test/gunicorn
LABEL maintainer="ethanzhang55@outlook.com"

CMD celery -A manage.my_celery worker --loglevel=info --hostname=celery_database_updator --queues=queue_update_case,queue_update_suite,queue_update_compare_result,queue_update_daily_compare_result,queue_update_samerpm_compare_result,queue_update_case_node,queue_create_case_node_multi_select --pool=gevent --concurrency=60
