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
# @Date    : 
# @License : Mulan PSL v2


#####################################

bind = '0.0.0.0:21500'  # 绑定ip和端口号
backlog = 10240  # 监听队列
chdir = '/opt/radiaTest/radiaTest-server'  # gunicorn要切换到的目的工作目录
timeout = 300  # 超时
worker_class = 'geventwebsocket.gunicorn.workers.GeventWebSocketWorker'

# workers = multiprocessing.cpu_count() * 2 + 1    #进程数
workers = 32
loglevel = 'info'  # 日志级别，这个日志级别指的是错误日志的级别，而访问日志的级别无法设置
access_log_format = '%(t)s %(p)s %(h)s "%(r)s" %(s)s %(L)s %(b)s %(f)s" "%(a)s"'  # 设置gunicorn访问日志格式，错误日志无法设置

accesslog = "log/gunicorn/access.log"  # 访问日志文件
errorlog = "log/gunicorn/error.log"  # 错误日志文件
