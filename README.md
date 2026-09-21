<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# radiaTest

radiaTest v2.0（原 Kronos）是面向 openEuler 内网测试环境的测试资源管理平台。系统以物理机和按需创建的虚拟机为核心资源，覆盖查询、占用、释放、凭据查看、导入导出、审计、VM 申请释放和 VM 电源操作。

## 项目状态

项目已具备可部署运行能力：

- 资源、测试、工单、通知和平台运行时功能规格(Spec)。
- 技术选型、领域模型和运行策略的架构决策记录(ADR)。
- 领域上下文和 Agent 协作规则。
- FastAPI 后端、健康检查和数据库迁移。
- Vben Admin 5.7.0 + Ant Design Vue 前端工程。
- 统一检查脚本 `scripts/check.sh`。
- 本地账号登录、JWT、用户模型、用户管理 API 和创建管理员 CLI。
- 资源台账数据库表、资源 API 和资源 upsert CLI。
- 前端登录、账号、资源、用户、日志、测试用例和测试任务页面。
- 审计日志写入能力、`ADMIN` 审计日志页面和按角色可见的租约日志页面。
- 资源占用、续期、释放、强制释放、懒释放和授权凭据查看。
- 资源 CSV 导入导出、租约 CSV 导入 API 和前端入口。
- VM 申请、本地 ISO 上传、申请记录、VM 列表、异步创建、异步释放和任务事件。
- VM Web VNC 控制台和 VM 电源状态、启动、关机、重启操作。
- 飞书应用配置 API 和管理页面、飞书身份绑定数据模型、Bot 长连接、Web 账号绑定、
  私聊资源查询卡片、VM 申请卡片和远程命令卡片。
- 测试管理模型、Mugen 用例索引同步、测试任务模板、可分享的任务详情页和 VM 测试任务执行 worker。
- 工单提交、分页筛选、可分享详情、管理员处理和评论功能。
- 站内通知、资源到期飞书提醒和每日通知调度。
- 统一 API 错误、请求追踪，以及 Worker 启动和读取懒检查的中断恢复。
- 远程 `dev`/`prod` 容器栈、部署脚本和服务器运行手册。

功能缺口：

- PAT。
- 测试任务真实 VM 环境联调。
- 资源池、XLSX 导入和连通性检查。

## 产品范围

radiaTest 当前聚焦 openEuler 内网测试资源管理：本地账号登录、`ADMIN`/`TSE`/`TE`
三类角色、物理资源和虚拟资源管理、资源租约、凭据授权查看、导入导出、VM
申请释放、Web VNC 控制台、VM 电源操作、审计与租约日志、飞书 Bot 私聊交互，以及
Mugen 测试用例、测试任务、任务模板、工单管理和通知管理。

资源管理行为以 [资源管理功能规格](docs/spec/0001-resource-management.md) 为准；
测试管理行为以 [测试管理功能规格](docs/spec/0002-test-management.md) 为准；
测试流水线行为以 [测试流水线功能规格](docs/spec/0003-test-pipeline.md) 为准；
工单管理行为以 [工单管理功能规格](docs/spec/0003-ticket-management.md) 为准；
通知行为以 [通知管理功能规格](docs/spec/0004-notification-management.md) 为准；
版本管理行为以 [版本管理功能规格](docs/spec/0006-version-management.md) 为准；
公共 API 和异步恢复行为以 [平台运行时规格](docs/spec/0005-platform-runtime.md) 为准；
关键取舍记录在 [ADR](docs/adr/)中。

## 技术栈(Technology Stack)

- 前端(Frontend)：Vue 3、TypeScript、Vben Admin、Ant Design Vue、pnpm。
- 后端(Backend)：FastAPI、SQLAlchemy 2.x 同步 ORM、Alembic、uv。
- 数据库(Database)：PostgreSQL。
- 异步任务(Async Task)：Celery worker、Celery Beat 和 Redis。
- 认证(Authentication)：Web 会话使用 JWT；脚本/API 令牌设计见认证权限 ADR。
- 部署(Deployment)：Docker Compose；远程 `dev` 和 `prod` 用 nginx 托管前端并反向代理 API。

## 仓库结构

```text
.
├── frontend/      # Vben Admin 前端应用
├── backend/       # FastAPI 模块化单体
├── deploy/        # Docker Compose、nginx、PostgreSQL 初始化文件
├── docs/
│   ├── adr/       # 架构决策记录(Architecture Decision Record, ADR)
│   ├── runbook/   # 部署、备份、恢复和运维手册
│   └── spec/      # 功能规格(Spec)
├── scripts/       # 检查、部署和辅助脚本
├── README.md
├── AGENTS.md
└── CONTEXT.md
```

## 文档入口

- [CONTEXT.md](CONTEXT.md)：领域语言、角色、状态模型和核心规则。
- [资源管理功能规格](docs/spec/0001-resource-management.md)：资源管理行为、页面、API 和验收标准。
- [测试管理功能规格](docs/spec/0002-test-management.md)：Mugen 用例同步、VM 测试任务、任务模板、环境套和 case 结果规则。
- [测试流水线功能规格](docs/spec/0003-test-pipeline.md)：update/release 流水线编排、RunJob 执行模型、看板和模块定义。
- [工单管理功能规格](docs/spec/0003-ticket-management.md)：工单状态、权限、评论、页面和 API 规则。
- [通知管理功能规格](docs/spec/0004-notification-management.md)：站内通知、资源到期提醒、工单通知和飞书投递规则。
- [平台运行时规格](docs/spec/0005-platform-runtime.md)：统一 API 错误、请求追踪和 Worker 中断恢复规则。
- [版本管理功能规格](docs/spec/0006-version-management.md)：RC 版本、里程碑（轮次）、软件包比对、结果筛选与交付导出。
- [架构决策记录(ADR)](docs/adr/)：技术选型、领域模型、运行策略和模块设计取舍，按编号递增、标题自描述。
- [实现计划](docs/plans/)：按 active/completed 分目录追踪进行中和已完成的目标。
- [服务器部署运行手册](docs/runbook/server-deployment.md)：远程 `dev`/`prod` 发布、备份、权限和故障处理约定。
- [AGENTS.md](AGENTS.md)：AI Agent 在本项目中的协作规则。

## 开发流程

radiaTest 的应用、PostgreSQL 和浏览器联调只在 Linux `dev` 环境运行。开发工作站
用于编辑代码、运行检查、提交并推送到 GitCode；部署命令在 radiaTest 服务器本机执行。

在仓库根目录运行检查：

```bash
./scripts/check.sh all
```

自动化测试必须使用隔离测试数据，不连接 `kronos_dev` 或 `kronos_prod`。需要
PostgreSQL 集成测试时，通过 `TEST_DATABASE_URL` 指向独立测试库，默认库名为
`kronos_test`；`test` 不是独立部署的网站环境。

开发工作站推送当前分支：

```bash
git push -u origin <分支名>
```

登录 radiaTest 服务器并部署到 `dev`：

```bash
cd /opt/kronos/dev/app
./scripts/deploy.sh <分支名>
```

部署成功后访问：

```text
http://<服务器地址>:8080
```

## 服务器初始化

首次安装时在 radiaTest 服务器执行：

```bash
mkdir -p /opt/kronos/dev
git clone https://gitcode.com/xu_yishen/kronos.git /opt/kronos/dev/app
bash /opt/kronos/dev/app/deploy/scripts/init-server.sh
```

脚本会在服务器上创建目录、clone HTTPS 仓库、安装 Docker、生成 dev/prod 配置和
Secret。已有 dev/prod 仓库会直接复用。完整的初始化和首次部署步骤见
[服务器部署运行手册](docs/runbook/server-deployment.md)。

## 正式发布

`dev` 验收通过并把 `main` 推送到 GitCode 后，在 radiaTest 服务器执行：

```bash
cd /opt/kronos/prod/app
./scripts/deploy.sh
```