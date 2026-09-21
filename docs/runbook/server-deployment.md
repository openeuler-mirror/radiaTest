<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# 服务器部署运行手册(Server Deployment Runbook)

本文说明如何把 radiaTest 部署到单台 openEuler 服务器。部署设计和取舍见
[ADR 0004：部署和开发流程](../adr/0004-deployment-and-dev-workflow.md)。

## 环境概览

服务器常驻两套相互隔离的环境：

| 环境 | 地址 | 用途 | 数据库 |
| --- | --- | --- | --- |
| `dev` | `http://<服务器地址>:8080` | 联调和人工验收 | `kronos_dev` |
| `prod` | `http://<服务器地址>` | 正式使用 | `kronos_prod` |
| `kimariyb-kronos` | `http://<服务器地址>:2420` | 专属实例 | `kimariyb_kronos` |

不部署 `test` 网站。自动化测试必须使用隔离测试数据，不连接 `kronos_dev` 或
`kronos_prod`。需要 PostgreSQL 集成测试时，通过 `TEST_DATABASE_URL` 指向独立
测试库，默认库名为 `kronos_test`。

关键路径：

```text
/opt/kronos/dev/app/              # dev Git 工作树
/opt/kronos/prod/app/             # prod Git 工作树
/etc/kronos/dev.env               # dev 配置和 Secret
/etc/kronos/prod.env              # prod 配置和 Secret
/data/backups/kronos/prod/        # prod 数据库备份
/data/kronos/uploads/dev/          # dev 用户上传的手动安装 ISO
/data/kronos/uploads/prod/         # prod 用户上传的手动安装 ISO
/opt/kimariyb-kronos/app/          # kimariyb-kronos Git 工作树
/etc/kimariyb-kronos.env           # kimariyb-kronos 配置和 Secret
/data/kronos/uploads/kimariyb-kronos/ # kimariyb-kronos 用户上传的手动安装 ISO
/var/lib/docker/                  # Docker 默认运行态数据
```

`kimariyb-kronos` 是独立的专属实例，不使用 `dev`、`prod` 的 Git 工作树、Compose
项目、数据库、Redis、网络、卷、应用 Secret 或上传目录。VM 申请仍使用现有 Compose
文件挂载的服务器 `/etc/kronos/ssh` 宿主机访问密钥；如需隔离该密钥，应单独调整 VM
宿主机访问配置。

## 专属 kimariyb-kronos 实例

首次安装在服务器以 root 执行：

```bash
mkdir -p /opt/kimariyb-kronos
git clone https://atomgit.com/kimariyb/kronos.git /opt/kimariyb-kronos/app
cp /opt/kimariyb-kronos/app/deploy/kimariyb.env.example /etc/kimariyb-kronos.env
chmod 600 /etc/kimariyb-kronos.env
```

编辑 `/etc/kimariyb-kronos.env`，为 `POSTGRES_PASSWORD`、`JWT_SECRET_KEY` 和
`RESOURCE_SECRET_KEY` 设置独立随机值；保留 `POSTGRES_DB=kimariyb_kronos` 和
`WEB_PORT=2420`。不要把该文件提交到 Git。

首次发布及后续发布均执行：

```bash
cd /opt/kimariyb-kronos/app
./scripts/deploy-kimariyb.sh
```

脚本只接受 `https://atomgit.com/kimariyb/kronos.git` 的 `main`，并以 Compose 项目
`kimariyb-kronos` 构建、迁移和启动服务。它不会操作 `kronos-dev` 或 `kronos-prod`
容器。每次迁移前会将该实例的数据库备份至
`/data/backups/kronos/kimariyb-kronos/`。部署后访问 `http://<服务器地址>:2420`。

每套环境的 Compose 服务：

```text
nginx      # 前端和 API 反向代理
backend    # FastAPI
worker     # Celery 异步任务
beat       # Celery 每日通知调度
bot        # 飞书 Bot 进程
postgres   # PostgreSQL
redis      # Celery broker/result backend
```
VM 申请释放的异步执行取舍见
[ADR 0005：VM 生命周期和异步执行](../adr/0005-vm-lifecycle-and-async-execution.md)。

命令执行位置约定：

- 开发工作站：编辑、检查、提交代码并推送到 GitCode，不直接连接 radiaTest 服务器。
- 服务器：以 root 执行初始化和运维命令。`./scripts/...` 必须在对应环境的
  `/opt/kronos/<环境>/app` 工作树中运行，脚本从当前绝对路径推导环境。

## 1. 推送代码

在开发工作站确认远端并把代码推送到 GitCode：

```bash
git remote -v
git push -u origin main
```

服务器只需能通过 HTTPS 读取 `https://gitcode.com/xu_yishen/kronos.git`。

## 2. 服务器初始化

首次安装时，在服务器直接 clone dev 工作树并执行初始化脚本：

```bash
mkdir -p /opt/kronos/dev
git clone https://gitcode.com/xu_yishen/kronos.git /opt/kronos/dev/app
bash /opt/kronos/dev/app/deploy/scripts/init-server.sh
```

脚本在服务器使用 root 执行以下操作：

- 安装 `curl`、`git`、`openssl` 和 `util-linux`。
- 创建 `/opt/kronos`、`/etc/kronos`、`/data/backups/kronos/prod` 和 dev/prod ISO
  上传目录。
- 通过 HTTPS 验证并 clone `https://gitcode.com/xu_yishen/kronos.git`。
- 安装 Docker Engine、Buildx 和 Docker Compose。
- 创建 `/etc/kronos/dev.env` 和 `/etc/kronos/prod.env`。
- 自动生成 dev/prod 不同的 `POSTGRES_PASSWORD`、`JWT_SECRET_KEY` 和 `RESOURCE_SECRET_KEY`。

如果 dev 或 prod 仓库已经存在，跳过对应的 `git clone`，直接复用仓库并校正
`origin` 后更新到 `origin/main`。

脚本不会覆盖已经存在的 `/etc/kronos/*.env`，避免重复执行时更换数据库密码。如果
需要重新生成配置，先删除对应 env 文件再执行初始化脚本。
生成后的固定差异：

| 配置 | dev | prod |
| --- | --- | --- |
| `APP_ENV` | `development` | `production` |
| `WEB_PORT` | `8080` | `80` |
| `POSTGRES_DB` | `kronos_dev` | `kronos_prod` |
| `DATABASE_URL` 数据库名 | `kronos_dev` | `kronos_prod` |
| `CELERY_WORKER_CONCURRENCY` | `2` | `4` |
| `MUGEN_REPO_URL` | `https://atomgit.com/openeuler/mugen.git` | 同 dev |
| `MUGEN_REPO_BRANCH` | `master` | 同 dev |

初始化后，登录服务器验证：

```bash
docker ps
docker compose version
git -C /opt/kronos/dev/app remote -v
```

直接使用 root 部署，减少用户、组和目录权限维护。只允许受信任人员获得服务器
root 权限。不要直接在服务器工作树中修改代码。

部署脚本会检查文件权限、必填变量、环境名、数据库名、端口和 worker 并发数。

已有环境缺少 worker 并发配置时，在服务器上补充：

```bash
printf '\nCELERY_WORKER_CONCURRENCY=2\n' >> /etc/kronos/dev.env
printf '\nCELERY_WORKER_CONCURRENCY=4\n' >> /etc/kronos/prod.env
```

## 3. 初始化 dev

在服务器的 dev 工作树执行：

```bash
cd /opt/kronos/dev/app
./scripts/deploy.sh
```

脚本会：

1. 要求服务器工作树干净。
2. 从 GitCode 获取 `origin/main` 并 detached checkout 到明确提交。
3. 构建镜像、启动 PostgreSQL 和 Redis、执行 Alembic 迁移并启动应用。
4. 检查 nginx、FastAPI、worker、beat、bot 和 PostgreSQL 链路。

dev 部署成功后访问：

```text
http://<服务器地址>:8080
```

登录服务器后创建 dev 管理员：

```bash
/opt/kronos/dev/app/deploy/scripts/app-cli.sh dev create-admin \
  --username admin \
  --display-name 管理员
```

密码由 CLI 交互输入，不写到命令参数、环境文件或 Git。

使用管理员账号登录 dev，确认：

- 登录成功。
- 页面显示当前用户。
- PostgreSQL 状态为正常。
- 资源管理页面可以打开。

如需启用飞书 Bot，在飞书开放平台分别为 `dev` 和 `prod` 创建独立应用，并为每个应用配置：

- 机器人能力和私聊消息权限。
- 长连接接收 `im.message.receive_v1`。
- 安全设置里的重定向 URL。

重定向 URL 只有端口不同：

| 环境 | 重定向 URL |
| --- | --- |
| `dev` | `http://<服务器地址>:8080/api/v1/integrations/feishu/oauth/callback` |
| `prod` | `http://<服务器地址>/api/v1/integrations/feishu/oauth/callback` |

然后用对应环境的 radiaTest 管理员进入“飞书集成”页面，保存该环境应用的 `app_id`、
`app_secret` 并启用 Bot。

飞书远程命令使用资源台账中保存的 SSH 用户和密码。目标资源需要能从 radiaTest
`bot` 容器访问 22 端口；命令输出只返回飞书卡片，定位失败优先查看 `bot` 日志。

如果需要申请 VM，先准备 VM 宿主机：

- 宿主机已安装并启用 libvirt。
- 宿主机已安装 `virsh`、`virt-install`、`qemu-img`、`curl`、`python3` 和
  `util-linux`。
- radiaTest backend 和 worker 使用 `/etc/kronos/ssh/id_rsa` 通过 SSH 公钥登录
  宿主机 root。把 `/etc/kronos/ssh/id_rsa.pub` 加到每台 VM 宿主机 root 的
  `authorized_keys`，并确认私钥权限为 `600`。
- 宿主机存在 `/var/lib/libvirt/images/kronos/cache/` 和
  `/var/lib/libvirt/images/kronos/instances/`，且空间位于用于 VM 镜像的 LVM 卷。
- VM 创建脚本只会机会式清理 `/var/lib/libvirt/images/kronos/cache/` 下超过
  30 天且未被 libvirt domain XML 引用的缓存文件，不清理 `instances/` 或其他目录。
- 宿主机可以访问内网 qcow2 镜像仓库和 DHCP 租约地址。
- 使用 Web VNC 控制台时，用户浏览器需要能访问宿主机自动分配的 VNC WebSocket
  端口；宿主机启用防火墙时，放行实际使用的端口范围。
- radiaTest 中对应物理资源为 `active`，填写 `arch`，并带 `vm-host` 标签。
- VM 宿主资源由 `ADMIN` 永久占用，避免作为普通测试资源发放。

如果服务器上还没有 VM 宿主登录 key，登录服务器后生成一组专用 key：

```bash
mkdir -p /etc/kronos/ssh
chmod 700 /etc/kronos/ssh
ssh-keygen -t rsa -b 4096 -f /etc/kronos/ssh/id_rsa -N '' -C kronos-vm-host
chmod 600 /etc/kronos/ssh/id_rsa
```

在服务器上把公钥复制到每台 VM 宿主机：

```bash
ssh-copy-id -i /etc/kronos/ssh/id_rsa.pub root@<VM宿主IP>
```

在服务器上验证 backend 和 worker 容器是否能登录宿主机：

```bash
docker exec -it kronos-dev-backend-1 sh -lc \
  'ssh -i /etc/kronos/ssh/id_rsa -o BatchMode=yes -o IdentitiesOnly=yes root@<VM宿主IP> true'
docker exec -it kronos-dev-worker-1 sh -lc \
  'ssh -i /etc/kronos/ssh/id_rsa -o BatchMode=yes -o IdentitiesOnly=yes root@<VM宿主IP> true'
```

资源台账和当前租约迁移优先使用 Web 资源管理页的 CSV 导入入口。先导入资源 CSV，
再导入当前租约 CSV；两类导入都支持先校验再确认，确认导入时由前端携带
`Idempotency-Key`。

如果需要应急维护资源台账，先把资源 JSON 放到服务器，再在服务器上执行：

```bash
/opt/kronos/dev/app/deploy/scripts/app-cli.sh dev upsert-resource --json-file - \
  < /root/kronos-resources.json
```

JSON 文件可以是单个资源对象，也可以是资源对象数组。真实机器密码只放在服务器
本地文件或数据库中，不提交到 Git。CLI 不导入租约；当前租约迁移仍使用 Web CSV
导入入口。

物理机 PXE 安装镜像（`physical_install_images`）同样用 CLI 维护。把镜像 JSON
放到服务器（如 `/etc/kronos/install-images.json`，每项含 `os_version`/`arch`/
`efi_url`/`repo_url`，数组），再执行：

```bash
/opt/kronos/dev/app/deploy/scripts/app-cli.sh dev seed-install-images --json-file - \
  < /etc/kronos/install-images.json
```

CLI 按 `(os_version, arch)` 幂等 upsert，可重复执行。镜像 URL 含内网地址，
只放在服务器本地，不提交到 Git。日常部署 `deploy-release.sh` 也会自动执行
此 seed（`/etc/kronos/install-images.json` 存在时），此处 CLI 用于手动补录或应急。

## 4. 初始化 prod

dev 验收通过并把 `main` 推送到 GitCode 后，在服务器执行：

```bash
cd /opt/kronos/prod/app
./scripts/deploy.sh
```

脚本会显示当前 prod 提交和目标提交，并要求输入完整的 `prod`。正式发布会在
Alembic 迁移前自动备份数据库。

部署脚本在数据库迁移后自动 seed 物理机 PXE 安装镜像
（`physical_install_images`）：`/etc/kronos/install-images.json` 存在时幂等
upsert，不存在则跳过。首次部署 prod 前确认该文件已就位，内容同 dev
（radiaTest 官方稳定镜像，内网 repo URL 只放服务器本地，不提交 Git）。

部署成功后访问：

```text
http://<服务器地址>
```

登录服务器后创建 prod 管理员：

```bash
/opt/kronos/prod/app/deploy/scripts/app-cli.sh prod create-admin \
  --username admin \
  --display-name 管理员
```

prod 管理员密码应与 dev 不同。

## 5. 日常发布

### 发布 dev

开发工作站先把目标分支推送到 GitCode，再在服务器的 dev 工作树执行：

```bash
cd /opt/kronos/dev/app
./scripts/deploy.sh <分支名>
```

省略分支名时默认部署 `main`。

### 发布 prod

把 `main` 推送到 GitCode 后，在服务器的 prod 工作树执行：

```bash
cd /opt/kronos/prod/app
./scripts/deploy.sh
```

部署脚本不会自动 push，也不支持跳过正式发布确认。

## 6. 状态和日志

在服务器查看 prod：

```bash
cd /opt/kronos/prod/app
./scripts/status.sh
```

在服务器查看 dev：

```bash
cd /opt/kronos/dev/app
./scripts/status.sh
```

在对应环境工作树查看日志：

```bash
./scripts/status.sh --logs
```

状态脚本会同时显示：

- `/`、`/data`、DockerRootDir 和 PostgreSQL 命名卷所在文件系统的空间。
- `docker system df` 的镜像、容器、卷和构建缓存占用。
- 可以人工复制执行的安全清理命令。
- `audit_logs`、`task_events` 和 `idempotency_records` 的估算行数和总大小。

VM 申请或释放异常时，先在 Web 详情页查看任务事件；任务事件不足以定位时，再查看目标
环境的 `worker` 日志。VM 电源操作是同步 API，不写任务事件；失败时先看页面返回的
`virsh` 错误摘要，再看目标环境的 `backend` 日志和宿主机状态。飞书 Bot 问题查看
`bot` 日志。API 可用性问题优先查看 `backend` 和 `nginx` 日志。

ISO 上传由 nginx 直接转发给后端流式写入对应环境的 `/data/kronos/uploads/<环境>/`。
上传路由允许最大 20 GB 请求体，关闭 nginx 请求体缓冲，连续 10 分钟没有收到上传数据
才会超时；这不是总上传时长限制。上传目录分别挂载到对应环境的 `backend` 和 `nginx`，
使用共享 SELinux 标签且不得交叉挂载 dev/prod。

上传失败时先看页面错误，再检查目标环境的 `backend` 和 `nginx` 日志以及 `/data` 空间。
平台要求上传后仍至少保留 10 GB 可用空间，且文件系统使用率低于 90%。完整 ISO 以
SHA-256 命名并保留 30 天，`.part` 临时文件保留 24 小时；清理在后续上传时触发，
不需要 cron 或 timer。不得手工清理其他 `/data` 目录或宿主机 libvirt 镜像目录。
发布前要求 `/data` 是独立挂载点；未挂载时部署会在创建上传目录前中止，避免文件误写入
根分区。

如果任务事件、`worker` 日志或 VM 电源操作返回
`Identity file /etc/kronos/ssh/id_rsa not accessible`，说明 radiaTest 服务器上的
VM 宿主登录私钥缺失，或没有通过 Compose 挂载到对应容器。先在服务器检查
`/etc/kronos/ssh/id_rsa` 是否存在、权限是否为 `600`；缺失时按“VM 宿主机”章节
生成 key，再用 `ssh-copy-id -i /etc/kronos/ssh/id_rsa.pub root@<VM宿主IP>` 写入目标宿主机。

任务事件保存在 PostgreSQL 的 `task_events` 表中，用于 Web 详情页展示；它们不是
Docker 容器日志，不受 Docker 日志轮转影响。容器 stdout/stderr 日志使用 Docker
`json-file` 轮转，每个容器最多保留 5 个 10 MB 文件。部署流程会自动清理超过
30 天的 `task_events` 和超过 7 天的 `idempotency_records`。`audit_logs` 不自动
清理，只在状态脚本中展示大小。

如需手动清理任务事件，登录服务器后执行：

```bash
/opt/kronos/<环境>/app/deploy/scripts/app-cli.sh <环境> cleanup-task-events --days 30
```

如需手动清理幂等记录，登录服务器后执行：

```bash
/opt/kronos/<环境>/app/deploy/scripts/app-cli.sh <环境> cleanup-idempotency-records --days 7
```

VM 申请长时间停留在 `creating` 或已开始后等待宿主并发槽位的 `queued` 时，先确认宿主机没有残留 domain 或 `.part`
文件；然后在 Web 页面手动刷新 VM 申请列表或申请事件。radiaTest 会把超过 60 分钟
仍处于 `creating/queued` 的申请标记为失败。该懒判断只修改 radiaTest 数据库状态，不连接
宿主机清理资源。

最后成功版本：

```text
/opt/kronos/dev/deployed-commit
/opt/kronos/prod/deployed-commit
```

部署历史：

```text
/opt/kronos/dev/deployments.jsonl
/opt/kronos/prod/deployments.jsonl
```

Git 工作树当前提交不等于成功上线版本，以 `deployed-commit` 为准。

## 7. 发布失败处理

发布脚本不会自动回滚应用、Alembic 或数据库。

失败时先查看脚本输出的失败步骤、备份路径和容器日志，再登录服务器检查：

```bash
cat /opt/kronos/<环境>/deployed-commit
tail -n 20 /opt/kronos/<环境>/deployments.jsonl
```

如果提示已有部署正在运行，说明目标环境的 `flock` 锁仍被另一个部署进程持有。
等待该进程结束，不要手工删除锁文件判断状态。

发布脚本会在构建镜像前检查 `/`、`/data`、DockerRootDir 和 PostgreSQL 命名卷空间。
任一检查对象可用空间低于 10 GB，或使用率达到 90%，发布会中止。Docker 构建缓存
超过 20 GB 时只提示人工清理，不自动删除。前端镜像构建后会先执行 `nginx -t`，
配置无效时不会进入应用停止阶段。

如果需要恢复旧应用代码，优先在 Git 中创建 revert 提交，推送后重新部署。数据库
已经迁移时，必须先确认旧代码与当前数据库结构兼容。

## 8. 备份和恢复

PostgreSQL 在线数据保存在 Docker 命名卷中，不会实时同步到 `/data`。数据库备份和
用户上传的临时 ISO 都位于 `/data`，ISO 不纳入数据库备份，按 30 天规则重新上传或
清理。

在服务器的 prod 工作树手工备份：

```bash
cd /opt/kronos/prod/app
./scripts/db.sh backup
```

正式部署自动创建的备份位于：

```text
/data/backups/kronos/prod/<时间>-<commit>.dump
```

部署成功后清理超过 30 天的自动部署备份；`manual-*` 手工备份不会被部署脚本
自动清理。不配置每日定时备份。

在服务器的 prod 工作树恢复数据库。恢复会覆盖正式数据库，只能在确认备份文件后
人工执行；执行时需要输入完整的 `prod` 确认。

```bash
cd /opt/kronos/prod/app
./scripts/db.sh restore /data/backups/kronos/prod/<备份文件>.dump
```

恢复脚本会停止 nginx 和 backend，重新创建 prod 数据库，导入备份，启动应用并
执行数据库健康检查。部署备份保存的是迁移前数据库结构。恢复前应确认备份与当前
部署的应用提交兼容；需要跨结构恢复时，先部署兼容的应用提交。不要自动运行
Alembic downgrade。

## 9. Docker 资源维护

部署脚本不会自动清理整台服务器的镜像或构建缓存。发布和状态检查只提示风险，
避免误删仍在使用的镜像、缓存或卷。

登录服务器后人工检查：

```bash
docker system df
docker image ls 'kronos-*'
```

清理 radiaTest 旧应用镜像时先预览：

```bash
/opt/kronos/prod/app/deploy/scripts/docker-cleanup.sh --dry-run
```

确认列表无误后执行：

```bash
/opt/kronos/prod/app/deploy/scripts/docker-cleanup.sh --run
```

该脚本只处理 `kronos-backend` 和 `kronos-frontend` 的 `dev-*`、`prod-*`
标签；每个仓库和环境保留最新 2 个镜像，并额外保留仍被容器引用或
`deployed-commit` 指向的镜像。

确认没有构建任务正在运行后，可以清理较旧的构建缓存和悬空镜像：

```bash
docker builder prune --filter until=720h
docker image prune --filter until=720h
```

确认镜像未被 dev、prod 或其他应用引用后再清理。不要对生产 Compose 执行：

```text
docker compose down -v
```

`-v` 会删除 PostgreSQL 命名卷。

## 10. 网络和安全限制

- 只有 nginx 暴露宿主端口。
- backend 和 PostgreSQL 只在 Compose 内部网络通信。
- Web VNC 控制台由浏览器直连 VM 宿主机 VNC WebSocket 端口，不经过 radiaTest nginx
  或 backend 代理。
- 真实 Secret 只保存在 `/etc/kronos/*.env`。
- dev/prod 使用不同密码和密钥。
- 通过 VPN 使用 HTTP，登录密码和设备凭据没有 HTTPS 传输保护。

具备内网域名和证书条件后，应切换 HTTPS。
