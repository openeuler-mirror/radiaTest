#!/usr/bin/env bash
# 根据容器环境变量生成 /etc/radiaTest/server.ini
# 注意：radiaTest 后端在 flask 进程启动时会"读取并删除"该文件（项目自身行为），
#       因此每次执行 flask 命令 / 启动后端前都需要重新生成本文件。
set -euo pipefail

sudo mkdir -p /etc/radiaTest
# 项目将日志/临时目录硬编码为生产路径 /opt/radiaTest/...（logging.json、gunicorn.conf.py 等），
# 在 dev 容器中补齐该目录树，并把 radiaTest-server 软链到工作区
sudo mkdir -p /opt/radiaTest/tmp/report /opt/radiaTest/tmp/requirement /opt/radiaTest/tmp/rpmcheck
sudo ln -sfn /workspace/radiaTest-server /opt/radiaTest/radiaTest-server

sudo tee /etc/radiaTest/server.ini >/dev/null <<EOF
[database]
SQLALCHEMY_DATABASE_URI = mysql+pymysql://radiaTest:${RADIATEST_DB_PASSWORD:-1234}@mariadb:3306/radiaTest?charset=utf8mb4

[server]
SERVER_IP = 0.0.0.0
SERVER_PORT = 21500

[redis]
REDIS_HOST = redis
REDIS_PORT = 6379
REDIS_SECRET = ${RADIATEST_REDIS_PASSWORD:-radiaTest1234}
REDIS_DB = 11
REDIS_SCRAPYSPIDER_DB = 5
REDIS_CA_CERTS = /etc/radiaTest/redis.crt

[celery]
BROKER_URL = amqp://${RADIATEST_RABBITMQ_USER:-radiaTest}:${RADIATEST_RABBITMQ_PASSWORD:-1234}@rabbitmq:5672/radiaTest
RESULT_BACKEND = redis://:${RADIATEST_REDIS_PASSWORD:-radiaTest1234}@redis:6379/10
SCRAPYSPIDER_BACKEND = redis://:${RADIATEST_REDIS_PASSWORD:-radiaTest1234}@redis:6379/5
SOCKETIO_PUBSUB = amqp://${RADIATEST_RABBITMQ_USER:-radiaTest}:${RADIATEST_RABBITMQ_PASSWORD:-1234}@rabbitmq:5672/radiaTest

[token]
TOKEN_SECRET_KEY = ${RADIATEST_TOKEN_SECRET_KEY:-dev-only-token-secret-change-me}
TOKEN_EXPIRES_TIME = 1800
LOGIN_EXPIRES_TIME = 14400
AES_KEY = ${RADIATEST_AES_KEY:-0123456789abcdef0123456789abcdef}
V5_ACCESS_TOKEN = ${V5_ACCESS_TOKEN:-}

[login]
AUTHORITY = gitee
OAUTH_REDIRECT_URI = ${RADIATEST_OAUTH_REDIRECT_URI:-}
OAUTH_HOME_URL = ${RADIATEST_OAUTH_HOME_URL:-}
OAUTH_GET_TOKEN_URL = ${RADIATEST_OAUTH_GET_TOKEN_URL:-}
OAUTH_CLIENT_ID = ${RADIATEST_OAUTH_CLIENT_ID:-}
OAUTH_CLIENT_SECRET = ${RADIATEST_OAUTH_CLIENT_SECRET:-}
OAUTH_GET_USER_INFO_URL = ${RADIATEST_OAUTH_GET_USER_INFO_URL:-}

[at]
OPENQA_URL = ${OPENQA_URL:-}

[majun]
MAJUN_API = ${MAJUN_API:-}
MAJUN_ACCESS_TOKEN = ${MAJUN_ACCESS_TOKEN:-}

[administrator]
ADMIN_USERNAME = ${RADIATEST_ADMIN_USERNAME:-}
ADMIN_PASSWORD = ${RADIATEST_ADMIN_PASSWORD:-}

[report]
TEST_REPORT_PATH = /opt/radiaTest/tmp/report

[requirement]
REQUIREMENT_ATTACHMENT_PATH = /opt/radiaTest/tmp/requirement

[rpmcheck]
RPMCHECK_FILE_PATH = /opt/radiaTest/tmp/rpmcheck
EOF

sudo chmod 0644 /etc/radiaTest/server.ini
# radiaTest 的 loads_config_ini() 会在读取后删除 server.ini（项目自身行为），
# 因此 /etc/radiaTest 必须对运行用户可写（与生产环境 radiaTest 用户持有该目录一致）
sudo chown "$(id -u):$(id -g)" /etc/radiaTest
echo "已生成 /etc/radiaTest/server.ini"
