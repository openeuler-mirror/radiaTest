#!/usr/bin/env bash
# 启动 radiaTest 后端（gevent + WebSocket），前台运行
set -euo pipefail

cd /workspace
# 同 post_install：确保 --user 安装的 Python 包在任意 UID 下可见
export HOME="${HOME:-/home/vscode}"
export PYTHONPATH="/home/vscode/.local/lib/python3.9/site-packages:${PYTHONPATH:-}"
# flask 进程启动会消费并删除 server.ini，先重新生成
bash /workspace/.devcontainer/init_server_ini.sh

cd /workspace/radiaTest-server
export FLASK_APP=/workspace/radiaTest-server/manage.py
exec flask run_gevent
