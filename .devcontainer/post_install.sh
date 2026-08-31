#!/usr/bin/env bash
# radiaTest devcontainer 依赖安装与初始化（幂等，可重复执行）
set -euo pipefail

cd /workspace
# vscode 被映射到 UID 0 时（宿主为 root），Python 会禁用 user site，
# 显式把 user site 加回 PYTHONPATH，保证 flask 等 --user 安装的命令可用
# 注意：updateRemoteUserUID 后 uid 0 可能同时匹配 root/vscode，getent 会解析错，
# 因此这里直接用镜像固定的 vscode 用户路径（openEuler 22.03 + Python 3.9）
export HOME="${HOME:-/home/vscode}"
export PYTHONPATH="/home/vscode/.local/lib/python3.9/site-packages:${PYTHONPATH:-}"

echo "==> [1/6] 初始化 /etc/radiaTest 配置"
sudo mkdir -p /etc/radiaTest
bash /workspace/.devcontainer/init_server_ini.sh
sudo cp -f /workspace/build/docker-compose/conf/casbinmodel.conf /etc/radiaTest/casbinmodel.conf

# 工作区属主检查：正常情况下 devcontainer 会通过 updateRemoteUserUID 把 vscode 映射到
# 宿主 UID，工作区应可写；若不可写则明确报错，避免静默改动用户仓库文件属主
if [ ! -w /workspace/radiaTest-web ] || [ ! -w /workspace/radiaTest-server ]; then
  echo "    [error] 工作区不可写（属主: $(stat -c '%U:%G' /workspace)）。"
  echo "            请确认 VS Code 已应用 updateRemoteUserUID（重新执行 Reopen in Container），"
  echo "            或手动执行: sudo chown -R \$(id -u):\$(id -g) /workspace"
  exit 1
fi

# 缓存卷/历史卷首次挂载为 root 属主，先修正属主避免 pip/npm 缓存告警
sudo mkdir -p /home/vscode/.cache/pip /home/vscode/.npm /commandhistory
sudo chown -R vscode:vscode /home/vscode/.cache/pip /home/vscode/.npm /commandhistory

# 等待 certgen 生成 redis TLS 证书（首次启动时容器编排先于 postCreate）
for _i in $(seq 1 60); do
  if [ -f /etc/radiaTest/certs/redis-ca.crt ]; then
    break
  fi
  sleep 1
done
if [ -f /etc/radiaTest/certs/redis-ca.crt ]; then
  sudo ln -sf /etc/radiaTest/certs/redis-ca.crt /etc/radiaTest/redis.crt
  echo "    redis TLS CA 已就绪: /etc/radiaTest/redis.crt"
else
  echo "    [warn] 未找到 redis TLS CA 证书，redis 相关功能将不可用"
fi

echo "==> [2/6] 安装 Python 依赖 (radiaTest-server)"
cd /workspace/radiaTest-server
# 同一容器内重复执行 postCreate（如 VS Code 重连触发）时跳过 pip 慢速解析：
# 已安装且 pip check 通过则直接跳过
if [ -f /home/vscode/.radiatest-pip-ok ] && python3 -m pip check >/dev/null 2>&1; then
  echo "    Python 依赖已安装（pip check 通过，跳过）"
else
  python3 -m pip install --user -r requirements.txt
  python3 -m pip check >/dev/null 2>&1 && touch /home/vscode/.radiatest-pip-ok || true
fi

echo "==> [3/6] unrar（可选，用例压缩包解压功能）"
sudo dnf install -y unrar >/dev/null 2>&1 \
  || echo "    [warn] dnf 源无 unrar 包，文件解压功能受限（可手动执行 radiaTest-server/install_rar.sh）"

echo "==> [4/6] 安装前端依赖 (radiaTest-web)"
cd /workspace/radiaTest-web
npm ci

echo "==> [5/6] 初始化数据库（幂等）"
cd /workspace/radiaTest-server
export FLASK_APP=/workspace/radiaTest-server/manage.py
bash /workspace/.devcontainer/init_server_ini.sh
if [ ! -d /workspace/radiaTest-server/migrations ]; then
  echo "    未发现迁移脚本目录，使用 db.create_all() 从模型初始化数据库（仅限 dev 环境）"
  echo "    如需改用迁移管理，可先执行: cd radiaTest-server && flask db init && flask db migrate"
  python3 -c "from manage import app, db; app.app_context().push(); db.create_all()"
else
  flask db upgrade
fi

echo "==> [6/6] 完成"
cat <<'MSG'

开发启动：
  后端：bash /workspace/.devcontainer/start_backend.sh
  前端：cd /workspace/radiaTest-web && npm run serve
  浏览器：http://localhost:8080

详细说明见 /workspace/.devcontainer/README.devcontainer.md
MSG
