<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0004：部署和开发流程(Deployment and Development Workflow)

## 状态

已接受(Accepted)。

## 背景

radiaTest 在单台 openEuler 服务器上开发和部署。系统避免 Kubernetes 和微服务，
保证开发环境与正式环境相互隔离、版本可追踪、数据库迁移有恢复点。VM 申请释放
需要的异步 worker 和 Redis 由 VM 生命周期 ADR 单独约束。

## 开发环境

远程 Linux `dev` 是唯一的应用开发运行环境，用于镜像构建、数据库迁移、前后端
联调和人工验收。开发工作站只用于编辑代码、运行检查、提交并推送到 GitCode，
不启动数据库、Uvicorn 或 Vite 开发服务。开发工作站通过 GitCode 交付代码，不
直接连接 radiaTest 服务器；初始化和发布命令在服务器本机执行。

服务器常驻两套浏览器可访问环境：

- `dev`：开发环境，宿主端口 `8080`。
- `prod`：正式环境，宿主端口 `80`。

服务器额外运行一个专属实例 `kimariyb-kronos`：它从
`https://atomgit.com/kimariyb/kronos.git` 的 `main` 部署，宿主端口为 `2420`。
该实例使用独立的 Compose 项目、Git 工作树、环境文件、上传目录、网络和命名卷；它不属于
`dev`、`prod` 或测试网站，也不复用它们的数据库或 Secret。

不部署第三套 `test` 网站。自动化测试必须自行准备和清理隔离测试数据，不得连接
`kronos_dev` 或 `kronos_prod`。需要 PostgreSQL 集成测试时，通过
`TEST_DATABASE_URL` 指向独立测试库，默认库名为 `kronos_test`。

两套环境共用 `deploy/docker-compose.server.yml`，但使用不同的 Compose 项目名、
Git 工作树、环境变量文件、PostgreSQL 容器、网络和命名卷：

```text
kronos-dev
kronos-prod
kimariyb-kronos
```

`dev` 与 `prod` 使用相同的构建后运行形态，不挂载源码，不启用 Uvicorn reload
或 Vite 开发服务器。

前端统一使用相对 `/api/v1` 路径。两套环境均由 nginx 托管前端，并将 `/api`
反向代理到同一 Compose 项目中的 backend。

backend 直接运行单个 Uvicorn 进程。如果需要更强的进程管理或更高
并发，再引入 Gunicorn 或多实例部署。

服务器只暴露各环境的 nginx 端口。backend 和 PostgreSQL 不发布宿主端口，只
通过各自 Compose 网络通信。VM 申请释放使用的 worker 和 Redis 同样不发布宿主端口。

每套环境的服务包含：

- `nginx`：托管前端并反向代理 API。
- `backend`：提供 FastAPI API。
- `worker`：执行 Celery 异步任务。
- `postgres`：保存业务状态。
- `redis`：作为 Celery broker/result backend。

## 发布模型

部署代码、Dockerfile、Compose、nginx 配置、ADR 和运行手册与应用代码放在同一个
Git 仓库中。服务器初始化和发布分别使用脚本：

```text
deploy/scripts/init-server.sh     # openEuler 初始化执行器
scripts/deploy.sh                 # 服务器本地发布入口
deploy/scripts/deploy-release.sh  # openEuler 端发布执行器
```

发布入口负责解析目标分支并切换到明确提交，再启动目标提交中的发布执行器。两者保持
分离，保证部署流程使用目标版本自带的构建、迁移和健康检查逻辑；如果合并，checkout
后当前 Bash 进程仍会继续执行旧提交中已经加载的脚本。

开发工作站负责：

1. 运行检查并确认工作区干净。
2. 提交代码并把目标分支推送到 GitCode。

服务器负责：

1. 初始化时创建目录、clone HTTPS 仓库、安装 Docker 并生成环境配置。
2. 从目标环境工作树推导 `dev` 或 `prod`，本地执行发布、状态及数据库命令。
3. 发布时从 GitCode HTTPS 远端获取指定分支。
4. detached checkout 到明确提交。
5. 按服务器 CPU 架构原生构建镜像。
6. 执行迁移、启动和健康检查。

不从开发工作站复制本地构建镜像，也不使用 `git pull` 隐式合并分支。

分支规则：

- `dev` 可以部署任意已经推送的分支。
- `prod` 只能部署 `main`。
- dev 未指定分支时默认部署 `main`。
- 发布入口必须从 `/opt/kronos/dev/app` 或 `/opt/kronos/prod/app` 执行，并由
  当前绝对路径推导目标环境。
- 部署脚本不执行 `git push`。
- 正式发布必须交互输入 `prod` 确认。

镜像以环境和 Git 提交哈希标记。Git 保存代码历史，不额外维护固定数量的发布目录
或旧镜像。

## 迁移和失败策略

Alembic 迁移由目标版本 backend 镜像的一次性容器执行，服务器宿主机不安装项目
Python、uv 或后端依赖。

应用发布不停止或重建 PostgreSQL，只更新 backend、worker 和 nginx；Redis 保持运行。

`prod` 发布顺序：

```text
磁盘预检
  -> 构建镜像
  -> 校验 nginx 配置
  -> 停止 nginx 和 backend
  -> pg_dump 到独立 /data 磁盘
  -> Alembic upgrade head
  -> 清理过期任务事件和幂等记录
  -> 启动 backend、worker 和 nginx
  -> 健康检查
```

部署在同一停启窗口内停止和启动 worker，并把 worker 健康状态纳入检查。worker
使用长停止宽限时间，让正在执行的 VM 创建或销毁任务尽量自然完成。`dev`
worker 并发数固定为 2，`prod` worker 并发数固定为 4。

`dev` 不自动备份，直接迁移和启动。

发布失败时：

- 立即停止并输出诊断信息。
- 不自动回滚应用。
- 不自动执行 Alembic downgrade。
- 不自动恢复数据库。

健康检查通过后才更新当前成功版本。发布前检查 `/`、`/data`、DockerRootDir 和
PostgreSQL 命名卷空间；可用空间低于 10 GB 或使用率达到 90% 时中止发布。
Docker 构建缓存超过 20 GB 时只提示人工清理，不自动删除。

自动部署备份保留 30 天；不增加每日定时备份。任务事件保留 30 天，已完成的幂等记录保留
7 天并随部署流程清理；处理中记录不自动删除。审计日志不自动清理，只在状态脚本中统计大小。

## 访问和敏感信息

服务器本地直接使用 root 用户部署。选择 root 是为了减少专用用户、Docker 组和
目录权限维护；只允许受信任人员获得服务器 root 权限。服务器读取 GitCode 仓库时
使用 HTTPS。

服务器环境的真实 Secret 保存在仓库外：

```text
/etc/kronos/dev.env
/etc/kronos/prod.env
```

dev/prod 的 PostgreSQL 密码、JWT 密钥及其他 Secret 必须相互独立。初始化脚本
只在配置文件不存在时生成 Secret；发布脚本只校验配置，不生成或覆盖 Secret。
需要重新生成配置时，管理员先删除对应 env 文件再重新执行初始化脚本。

未配置内网域名和证书体系，通过 VPN 使用服务器 IP 和 HTTP 访问。这是已知的
传输加密限制；具备内网 DNS 和证书条件后应切换 HTTPS。

## 运行策略

- nginx、backend、worker、postgres 和 redis 使用 `restart: unless-stopped`。
- 容器日志写 stdout/stderr，并使用 Docker `json-file` 轮转。
- 部署使用每环境独立的 `flock`，并发发布立即失败。
- 部署历史写入每环境 JSON Lines 文件。
- 部署脚本不自动执行 Docker 全局清理。

## 检查入口

开发工作站和 CI 共用一个参数化检查脚本。检查应在提交前或 CI 中执行，部署脚本
不重复执行全量检查：

```text
scripts/check.sh all
scripts/check.sh backend
scripts/check.sh frontend
scripts/check.sh docs
scripts/check.sh scripts
scripts/check.sh quick
```

这些检查不启动应用开发环境。实际镜像、迁移、服务链路和浏览器验收在远程
`dev` 完成。新增检查继续扩展该入口，不创建平行的检查脚本。

## 影响

- 只有远程 Linux 服务器需要维护应用运行依赖。
- `dev` 和 `prod` 可以运行不同提交，数据库和容器生命周期相互独立。
- 单机 Compose 发布简单且可追踪，但接受短暂停机。
- 数据库迁移失败需要管理员按运行手册处理。
- 可以把 Git 触发改为 CI/CD 和不可变镜像发布，而不改变应用的 Compose 拓扑。
