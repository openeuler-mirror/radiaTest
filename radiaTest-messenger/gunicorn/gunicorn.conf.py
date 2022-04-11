# gunicorn.conf.py
bind = '0.0.0.0:21510'      #绑定ip和端口号
backlog = 10240                #监听队列
chdir = '../'  #gunicorn要切换到的目的工作目录
timeout = 30      #超时
worker_class = 'geventwebsocket.gunicorn.workers.GeventWebSocketWorker'

# workers = multiprocessing.cpu_count() * 2 + 1    #进程数
workers = 32
# threads = 32 #指定每个进程开启的线程数
loglevel = 'info' #日志级别，这个日志级别指的是错误日志的级别，而访问日志的级别无法设置
access_log_format = '%(t)s %(p)s %(h)s "%(r)s" %(s)s %(L)s %(b)s %(f)s" "%(a)s"'    #设置gunicorn访问日志格式，错误日志无法设置

"""
其每个选项的含义如下：
h          remote address
l          '-'
u          currently '-', may be user name in future releases
t          date of the request
r          status line (e.g. ``GET / HTTP/1.1``)
s          status
b          response length or '-'
f          referer
a          user agent
T          request time in seconds
D          request time in microseconds
L          request time in decimal seconds
p          process ID
"""
accesslog = "log/gunicorn_access.log"      #访问日志文件
errorlog = "log/gunicorn_error.log"        #错误日志文件
