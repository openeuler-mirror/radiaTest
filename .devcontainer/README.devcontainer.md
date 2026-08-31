# radiaTest devcontainer 使用说明

## 判定结论：🟡 有条件（compose 模式）

依据 openEuler devcontainer 评估矩阵，radiaTest 判定为"有条件"：

- **范围内**：`radiaTest-server`（Flask + gevent/gunicorn）与 `radiaTest-web`（Vue3 + Vue CLI 5）本地开发启动；中间件 mariadb / redis(TLS) / rabbitmq 一键拉起；数据库自动初始化（若仓库已提交迁移脚本则执行 `flask db upgrade`，否则用 `db.create_all()` 从模型建库，仅限 dev 环境）。
- **刻意不做**：生产 nginx + SSL 证书部署、celery worker/beat 全量编排、gitee OAuth / OpenQA / MaJun 等外部平台集成（需凭据与内网可达性，见"已知限制"）。本仓库无自动化测试套件，故无测试门禁环节。

## 快速开始

1. （可选）准备环境变量：`cp .devcontainer/.env.example .env`，按需填写。
2. VS Code 打开仓库根目录，执行 **"Reopen in Container"**；或命令行：

   ```bash
   devcontainer up --workspace-folder .
   ```

3. 首次进入会自动执行 `post_install.sh`：安装 Python/前端依赖、生成 `/etc/radiaTest/server.ini` 与 casbin 配置、初始化数据库（幂等，可重复执行）。
4. 启动服务：

   ```bash
   # 终端 1：后端（gevent + WebSocket，端口 21500）
   bash .devcontainer/start_backend.sh

   # 终端 2：前端 dev server（端口 8080）
   cd radiaTest-web && npm run serve
   ```

   浏览器访问 http://localhost:8080。

> 前端代理：本配置**不改动** `radiaTest-web/vue.config.js`，前端默认沿用仓库原配置（`/api` 指向远程部署环境 `https://116.204.98.119:8080/`）。如需在容器内连接本地后端（`http://127.0.0.1:21500/`），请手动修改 `vue.config.js` 的 `devServer.proxy`。

## 服务与端口

| 服务 | 镜像 | 容器内端口 | 宿主机映射 | 说明 |
|---|---|---|---|---|
| app | 自建（openEuler 22.03-lts） | 8080 / 21500 | 8080 / 21500 | 前后端开发环境 |
| mariadb | mariadb:10.5 | 3306 | 13306 | 数据库 radiaTest / 用户 radiaTest |
| redis | redis:7 | 6379（仅 TLS） | 16379 | 缓存/任务状态，TLS 自签证书 |
| rabbitmq | rabbitmq:3-management | 5672 / 15672 | 5673 / 15673 | celery broker / 管理台 |
| certgen | 自建（复用 dev Dockerfile） | — | — | 一次性生成 redis TLS 证书 |

## 配置与凭据

- 开发默认凭据（中间件密码等）为本地 dev-only 值，写在 `docker-compose.yml` 与 `.env.example`，不包含任何生产凭据。
- 外部平台 token（gitee / OpenQA / MaJun）通过 `.env` 或宿主环境变量注入：
  `remoteEnv` 使用 `${localEnv:KEY:}` 占位，未设置时为空。
- `/etc/radiaTest/server.ini` 由 `.devcontainer/init_server_ini.sh` 根据容器环境变量生成。
  **注意（项目自身行为）**：flask 进程启动时会读取并删除该文件，因此每次执行 flask 命令或启动后端前都必须重新生成；`start_backend.sh` 已处理。
- 项目把日志/临时目录硬编码为生产路径 `/opt/radiaTest/...`（logging.json、gunicorn.conf.py 等），
  初始化脚本会自动补齐目录树并把 `/opt/radiaTest/radiaTest-server` 软链到工作区，无需手动处理。
- `casbinmodel.conf` 启动时从 `build/docker-compose/conf/` 复制到 `/etc/radiaTest/`。

## 为什么 redis 需要 TLS

radiaTest 后端 `RedisClient` 固定使用 `redis.connection.SSLConnection`，`celeryconfig.py` 的 result backend 也硬编码 `ssl_cert_reqs=required&ssl_ca_certs=/etc/radiaTest/redis.crt`。因此 dev 环境由 `certgen` 服务生成自签 CA 与服务端证书（SAN: `redis`），redis 以 TLS 模式启动，CA 证书挂载到 app 容器 `/etc/radiaTest/redis.crt`。证书只存在于命名卷，不提交仓库。

## 资源要求与缓存

- 内存 >= 4GB、磁盘 >= 10GB（前端 webpack 构建、Python 依赖、中间件数据）。
- 缓存使用命名卷持久化：`radiatest-pip`（pip）、`radiatest-npm`（npm）、`radiatest-history`（命令历史）。compose 模式下必须挂在 app 服务 `volumes`（devcontainer.json 的 `mounts` 不生效）。

## 已知限制与边界

- **无测试套件**：本仓库没有自动化测试，devcontainer 只保证依赖安装与服务可启动。
- **首次 postCreate 较慢**：pip 会对每个固定版本依赖联网解析（受网络延迟影响约 10-20 分钟）；
  同一容器内重复执行时已有标记会跳过 pip。npm ci 首装约 5-10 分钟。
- **工作区属主**：VS Code 通过 `updateRemoteUserUID` 把容器内 `vscode` 映射到宿主 UID 后写入工作区；
  若直接 `docker exec` 且工作区不可写，post_install 会明确报错并提示处理方式，不会擅自改动仓库属主。
- **登录/外部平台**：gitee OAuth 登录、OpenQA、MaJun、gitee 机器人等需要 `.env` 中配置对应凭据且网络可达；未配置时仅服务本身可用。管理员初始化需设置 `RADIATEST_ADMIN_USERNAME/PASSWORD` 后手动执行 `flask init_asr`。
- **celery 全量 worker 未编排**：涉及异步任务（用例文件解析、openqa_reader 等）的接口需要 celery worker 与外部平台配合，dev 容器默认不启动；任务结果写入走 redis TLS。
- **aarch64**：部分 Python 依赖（如 pandas 1.3.4）在 aarch64 缺少预编译 wheel，可能需要源码编译（gcc/gfortran），首次安装耗时明显。
- **unrar**：openEuler 默认源无 unrar 包，用例压缩包解压功能默认不可用；可手动执行 `radiaTest-server/install_rar.sh`（需可访问 rarlab.com）。
- **镜像源**：容器内 dnf / pip / npm 使用默认公网源；企业内网环境请通过 `ARG`/`ENV`/配置文件注入内网镜像，本配置不写死任何内网地址。
