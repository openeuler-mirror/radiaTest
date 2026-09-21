<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# radiaTest 架构设计文档

## 1、需求描述

radiaTest 是面向 openEuler 内网测试环境的测试资源管理平台。系统以物理机和按需创建的虚拟机为核心资源，覆盖资源台账管理、租约流转、凭据保护、VM 申请与释放、Web VNC 控制台、飞书 Bot 集成、Mugen 测试任务执行和测试流水线编排（含 update / release 等类型）。系统解决内网测试环境中测试机器分配混乱、凭据散落、VM 创建手工化、测试执行缺乏编排和 update 测试缺乏统一看板等问题。

### 1.1、受益人

| 角色 | 角色描述 |
| --- | --- |
| `ADMIN` | 平台管理员。管理用户和角色、管理全部资源和资源池、导入导出资源、查看全部凭据和审计日志、占用关键资源、强制释放任意租约 |
| `TSE` | 测试系统工程师。创建和编辑资源、管理资源池、占用非关键资源、强制释放 `TE` 租约、查看全部租约事件 |
| `TE` | 测试工程师。查看资源公共信息、占用和释放非关键资源、续期自己的租约、申请 VM、创建和查看测试任务 |
| 飞书用户 | 通过飞书私聊 Bot 查询资源、申请 VM 和执行远程命令的已绑定身份用户 |
| 前端界面 | 通过 nginx 托管的 Web UI 消费 REST API，权限检查用于用户体验，后端鉴权为最终边界 |
| 测试流水线负责人 | 通过 Pipeline 看板触发 update / release 等测试、查看模块×架构矩阵结果、下钻查看子用例和日志；管理 direct_run 类型的流水线类型注册 |

### 1.2、依赖组件

| 组件 | 组件描述 | 可获得性 |
| --- | --- | --- |
| PostgreSQL 16 | 主数据库。提供关系完整性、事务、行锁、JSONB 和数组字段 | Docker Hub 官方镜像，开源 |
| Redis 7 | Celery broker 和 result backend。只承担任务队列和结果存储 | Docker Hub 官方镜像，开源 |
| Python 3.12 | 后端运行时。FastAPI + SQLAlchemy 2.x 同步 ORM | 官方 Docker Hub 镜像，开源 |
| Node.js 24 | 前端构建时。Vue 3 + Vben Admin + Ant Design Vue | 官方 Docker Hub 镜像，开源 |
| nginx 1.28 | 前端静态文件托管和 API 反向代理 | 官方 Docker Hub 镜像，开源 |
| Docker Engine 29.x | 容器运行时。构建镜像和运行 Compose 服务 | 官方静态二进制包，开源 |
| Docker Compose v5.x | 多容器编排。dev/prod 双环境隔离 | 官方 Docker CLI 插件，开源 |
| libvirt / virsh | VM 宿主机上的虚拟化管理。VM 创建、销毁和电源操作 | 宿主机预装，开源 |
| Fernet (cryptography) | 应用层对称加密。SSH/BMC 凭据加密存储 | Python cryptography 库，开源 |
| 飞书开放平台 | Bot 长连接和 OAuth 回调。私聊命令和卡片交互 | 飞书 SaaS，需注册应用 |
| Mugen 测试框架 | openEuler 测试框架。suite/case 索引和测试执行入口 | atomgit.com/openeuler/mugen，开源 |

### 1.3、License

radiaTest 后端和部署脚本使用项目仓库声明的 License。前端基于 Vben Admin 5.7.0（MIT License）二次开发。依赖的开源组件均以各自 License 分发。

---

## 2、架构目标

### 2.1、架构目标

- **简单优先**：单团队内网使用，避免过度设计。不引入 K8s、微服务拆分或消息总线。
- **状态一致性**：租约并发、VM 生命周期和凭据变更必须状态可推理。业务状态以 PostgreSQL 为准，Redis 只做队列。
- **安全边界清晰**：前端权限只用于用户体验，后端鉴权是最终边界。凭据应用层加密，审计覆盖敏感操作。
- **可部署可回滚**：单台 Linux 服务器 Docker Compose 部署；dev/prod 隔离；prod 部署前自动备份；回滚优先用 Git revert。
- **懒释放优先**：过期租约和 VM 异常状态通过用户触发的读取收敛，不引入后台轮询或定时器。
- **Pipeline 编排**：测试流水线作为 TestJob 之上的编排层，支持多版本×多架构全并行、模块模板化、物理机执行、子用例解析和统一看板。类型分 A 类（代码驱动，如 update）和 B 类（数据驱动，如 release）。

### 2.2、关键架构需求

| 需求名称 | 需求描述 | 需求类别 | 需求优先级 |
| --- | --- | --- | --- |
| 租约并发安全 | 同一资源同一时间只有一个活跃租约；租约操作使用 `lease_id` 避免旧请求影响下一任租约 | 功能/可靠性 | 高 |
| 凭据保护 | SSH/BMC 凭据必须 Fernet 加密存储；查看执行后端鉴权但不记录查看行为；修改写审计 | 安全性 | 高 |
| VM 异步创建 | VM 创建耗时超 2 分钟，必须异步执行；用户提交后得到申请单；失败回滚或提示管理员 | 功能/可靠性 | 高 |
| 幂等写接口 | 占用、释放、续期、VM 申请/释放和导入确认使用 `Idempotency-Key` 去重 | 可靠性 | 高 |
| 环境隔离 | dev 和 prod 使用独立数据库、独立 Secret 和独立 Compose 项目 | 安全性/可靠性 | 高 |
| 飞书 Bot 隔离 | Bot 长连接进程独立于 FastAPI Web 进程；每套环境独立飞书应用 | 功能 | 中 |
| 测试任务编排 | 测试任务固定 Mugen 版本；多套环境并发执行；VM 按需创建和销毁 | 功能 | 中 |
| 数据可追溯 | 用户不物理删除；审计日志、租约事件和任务事件可追溯历史 | 可靠性/安全性 | 高 |

### 2.3、假设和约束

- 服务器为单台 openEuler 24.03 (LTS-SP4) aarch64，内网可达。
- 应用、PostgreSQL 和浏览器联调只在远程 Linux 服务器运行；开发工作站只用于编辑、检查、提交和触发部署。
- 通过 VPN 使用 HTTP，登录密码和设备凭据没有 HTTPS 传输保护；具备内网域名和证书条件后应切换 HTTPS。
- VM 宿主机已预装 libvirt、virsh、virt-install、qemu-img、curl、python3 和 util-linux。
- VM 宿主机可访问内网 qcow2 镜像仓库和 DHCP 租约地址。
- 用户浏览器需要能访问 VM 宿主机自动分配的 VNC WebSocket 端口。
- Docker Hub 在国内网络可能不可达，需要配置镜像加速。
- 不支持 Web 自助注册、OAuth/SSO 登录、用户自改用户名和物理删除用户。
- 资源池只用于分类和筛选，不参与权限控制。
- 不提供任意远程 Shell 能力；VM 宿主操作只调用仓库内固定脚本入口。

### 2.4、架构原则

| 原则 | 原则描述 | 举例 |
| --- | --- | --- |
| 单向依赖原则 | 模块间仅允许上层调用下层；路由层调用 service 层，service 层调用 ORM 和基础设施 | `router.py` → `service.py` → `models.py` |
| 业务逻辑下沉原则 | 业务规则放在 Service 或 Domain Module 中，不只写在 Router 里 | 租约并发检查在 `leases/service.py`，不在 `leases/router.py` |
| 后端鉴权最终边界原则 | 前端权限检查只改善用户体验；后端 API 鉴权才是最终权限边界 | 前端隐藏审计菜单，后端 `audit/router.py` 校验 `ADMIN` 角色 |
| 懒释放原则 | 过期租约和 VM 异常状态通过用户触发的读取收敛，不引入后台轮询、定时器或 worker | VM 申请超 60 分钟在页面刷新时标记失败，不主动扫描 |
| 同步 ORM 原则 | 使用同步 SQLAlchemy，因为租约涉及事务、锁和状态变更，同步模型更容易推理 | `Session` 同步事务，`with_for_update` 行锁 |
| 镜像只读原则 | VM 宿主登录私钥挂载为只读，不在容器内修改基础设施凭据 | `/etc/kronos/ssh:/etc/kronos/ssh:ro` |
| Secret 不入 Git 原则 | 真实 Secret 只保存在 `/etc/kronos/*.env` 或部署环境变量中 | `.env.example` 只含占位值 |

---

## 3、用例视图

### 3.1、上下文模型

关注系统边界，定义系统与外部环境的交互，定义系统的范围、职责和边界。

#### 3.1.1、上下文视图

```text
┌──────────────────────────────────────────────────────────────────┐
│                         外部参与者                                │
│                                                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐     │
│  │ ADMIN    │  │ TSE      │  │ TE       │  │ 飞书用户     │     │
│  │ 管理员   │  │ 系统工程师│  │ 测试工程师│  │ (已绑定身份) │     │
│  └─────┬────┘  └─────┬────┘  └─────┬────┘  └──────┬──────┘     │
│        │             │             │               │            │
│        │  HTTP        │  HTTP       │  HTTP         │ 飞书长连接 │
│        ▼             ▼             ▼               ▼            │
│  ┌─────────────────────────────────────────────────────────┐     │
│  │                    radiaTest 平台                          │     │
│  │  ┌────────┐  ┌──────────┐  ┌────────┐  ┌────────────┐  │     │
│  │  │ nginx  │  │ backend  │  │ worker │  │ bot        │  │     │
│  │  │ (Web)  │  │ (FastAPI)│  │(Celery)│  │ (飞书长连接)│  │     │
│  │  └────────┘  └──────────┘  └────────┘  └────────────┘  │     │
│  │  ┌────────────────┐  ┌────────┐                         │     │
│  │  │ PostgreSQL     │  │ Redis  │                         │     │
│  │  └────────────────┘  └────────┘                         │     │
│  └─────────────────────────────────────────────────────────┘     │
│        │             │               │                            │
│        │ SSH         │ HTTP          │ HTTP                      │
│        ▼             ▼               ▼                            │
│  ┌──────────┐  ┌───────────┐  ┌──────────────┐                  │
│  │ VM 宿主机 │  │ 镜像仓库   │  │ Mugen 仓库    │                  │
│  │ (libvirt)│  │ (qcow2)   │  │ (atomgit)    │                  │
│  └──────────┘  └───────────┘  └──────────────┘                  │
│        │                                                         │
│        │ VNC WebSocket                                           │
│        ▼                                                         │
│  ┌──────────┐                                                    │
│  │ 浏览器    │  (直连宿主机 VNC，不经过 radiaTest)                    │
│  └──────────┘                                                    │
└──────────────────────────────────────────────────────────────────┘
```

#### 3.1.2、外部接口描述

| 接口编号 | 类型 | 接口描述 | 规格 |
| --- | --- | --- | --- |
| IF-01 | HTTP (REST) | 浏览器访问 Web UI 和 API | nginx 对外暴露 `WEB_PORT`（dev:8080, prod:80）；API 前缀 `/api/v1` |
| IF-02 | HTTP (REST) | 飞书 OAuth 回调 | `GET /api/v1/integrations/feishu/oauth/callback`；重定向 URL 端口区分 dev/prod |
| IF-03 | 飞书长连接 | Bot 接收私聊消息和卡片交互 | `im.message.receive_v1` 事件；只处理私聊，不处理群聊 |
| IF-04 | SSH | backend/worker → VM 宿主机 | 使用 `/etc/kronos/ssh/id_rsa` 公钥登录宿主机 root；执行固定脚本 |
| IF-05 | HTTP | backend/worker → 镜像仓库 | 从内网 HTTP 目录解析 qcow2 镜像列表和 DHCP 租约 |
| IF-06 | HTTPS | worker → Mugen 仓库 | `git clone` Mugen 用例索引 |
| IF-07 | SSH | bot → 目标资源 | 飞书远程命令执行；使用资源保存的 SSH 用户和密码，不复用宿主脚本私钥 |
| IF-08 | WebSocket | 浏览器 → VM 宿主机 VNC | 浏览器直连宿主机 VNC WebSocket 端口，不经过 radiaTest 代理 |
| IF-09 | virsh | backend → VM 宿主机 | VM 电源操作（启动/关机/重启/状态查询）；同步执行 |

### 3.2、USE-CASE 模型

#### 3.2.1、USE-CASE 视图

```text
┌─────────────────────────────────────────────────────────────┐
│                         ADMIN                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ 用户管理  │  │ 资源管理  │  │ 导入导出  │  │ 审计日志  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐      │
│  │ 强制释放  │  │ 凭据查看  │  │ 飞书应用配置         │      │
│  │ 任意租约  │  │ (全部)    │  │                      │      │
│  └──────────┘  └──────────┘  └──────────────────────┘      │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                         TSE                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ 资源创建  │  │ 资源编辑  │  │ 占用资源  │  │ 续期租约  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────────┐      │
│  │ 释放租约  │  │ 强制释放  │  │ 租约事件 (全部)       │      │
│  └──────────┘  │ TE 租约   │  └──────────────────────┘      │
│                └──────────┘                                 │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                         TE                                   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ 查看资源  │  │ 占用资源  │  │ 释放租约  │  │ 续期租约  │   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ VM 申请  │  │ VM 释放  │  │ VM 电源  │                   │
│  └──────────┘  └──────────┘  └──────────┘                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐                  │
│  │ Web VNC  │  │ 测试任务  │  │ 测试用例  │                  │
│  └──────────┘  └──────────┘  └──────────┘                  │
│  ┌──────────┐                                               │
│  │租约事件   │                                               │
│  │ (自己)    │                                               │
│  └──────────┘                                               │
└─────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────┐
│                      飞书用户                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ 资源查询  │  │ VM 申请  │  │ 远程命令  │  │ 凭据查看  │   │
│  │ (卡片)    │  │ (卡片)    │  │ (SSH)    │  │ (沿用权限)│   │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘   │
└─────────────────────────────────────────────────────────────┘
```

### 3.2、逻辑视图

结合 USE-CASE，分解软件功能模块，识别架构需求和模块间交互关系。

```text
┌─────────────────────────────────────────────────────────────────┐
│                         API 层 (api/router.py)                  │
│  挂载所有模块 router 到 /api/v1 前缀                              │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                      业务模块层 (modules/)                       │
│                                                                 │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐ │
│  │ auth    │ │ users   │ │resources│ │ leases  │ │ vms      │ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └──────────┘ │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌──────────┐ │
│  │ feishu  │ │ audit   │ │ tasks   │ │ test_   │ │ idempot.  │ │
│  │         │ │         │ │         │ │ mgmt    │ │           │ │
│  └─────────┘ └─────────┘ └─────────┘ └─────────┘ └──────────┘ │
│  ┌─────────┐                                                     │
│  │pipelines│ 流水线编排层（A 类代码驱动 + B 类数据驱动）            │
│  │         │ Pipeline Type 注册 → Pipeline → Run → RunJob → TestJob │
│  │         │ repodata 解析 + case_planner + log_collector            │
│  └─────────┘                                                     │
│                                                                 │
│  每个模块: router → service → models                            │
│  router: HTTP 参数解析 + 依赖注入，不含业务规则                    │
│  service: 业务逻辑 + 事务 + 审计写入                              │
│  models: ORM 模型 + 表结构                                       │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                     基础设施层 (core/ + db/)                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐    │
│  │ config   │  │ security │  │credentials│  │ process_runner│   │
│  │ (Settings)│  │ (JWT)   │  │(Fernet)  │  │ (virsh/SSH)  │    │
│  └──────────┘  └──────────┘  └──────────┘  └──────────────┘    │
│  ┌──────────────────────────────────────────────────────┐      │
│  │ db/session.py (Session 工厂 + get_db 依赖)             │      │
│  │ db/base.py (Declarative Base)                         │      │
│  └──────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────┘
```

**核心实体关系：**

```text
User ──▶ ResourceLease ──▶ Resource
 │         │                  │
 │         └─▶ LeaseEvent     ├─▶ PhysicalResourceSpec
 │                            └─▶ VirtualResourceSpec
 │
 ├──▶ AuditLog
 ├──▶ UserIdentity (飞书绑定)
 ├──▶ VMRequest ──▶ TaskEvent
 └──▶ TestJob
       ├─▶ TestEnvSet
       │     ├─▶ TestEnvNode
       │     └─▶ TestCaseRun
       └─▶ TestCaseRun

MugenCase (用例索引，独立表)
```

**资源模型：** 统一 `Resource` 表 + 类型规格扩展表。三个状态字段独立存储：
- `management_status`：`active` / `maintenance` / `disabled`
- `connectivity_status`：`unknown` / `reachable` / `unreachable`
- `occupancy_status`：`idle` / `occupied` / `expired`

**租约模型：** `ResourceLease` 使用部分唯一索引保证活跃租约唯一：
```sql
UNIQUE INDEX uq_resource_leases_active_resource
  ON resource_leases (resource_id)
  WHERE released_at IS NULL
```
非管理员租约必须有 `expected_ends_at`（最长 14 天）；`ADMIN` 可创建永久租约。过期租约使用懒释放，不主动扫描。

### 3.3、开发视图

逻辑视图到代码模型的映射：

```text
kronos/
├── frontend/                    # 前端工程 (Vben Admin monorepo)
│   ├── apps/web-antd/           # 主应用
│   │   └── src/
│   │       ├── views/           # 12 个页面目录 (resources, virtual-machines, ...)
│   │       ├── api/             # API 请求封装
│   │       ├── router/          # 路由和权限守卫 (guard.ts, access.ts)
│   │       ├── store/           # Pinia 状态管理
│   │       └── adapter/         # Vben Admin 适配层
│   ├── packages/                # 共享包
│   └── internal/                # 内部工具
│
├── backend/                     # 后端工程 (FastAPI 模块化单体)
│   ├── app/
│   │   ├── main.py              # FastAPI 应用工厂
│   │   ├── api/router.py        # 路由聚合
│   │   ├── core/                # 基础设施 (config, security, credentials, process_runner)
│   │   ├── db/                  # Session 工厂和 Declarative Base
│   │   ├── modules/             # 11 个业务模块 (每个: models/schemas/service/router)
│   │   ├── bot.py               # 飞书 Bot 进程入口
│   │   ├── worker.py            # Celery worker 入口
│   │   └── cli.py               # 管理 CLI (create-admin, cleanup-*, upsert-resource)
│   ├── alembic/                 # 数据库迁移脚本
│   ├── tests/                   # 测试
│   └── pyproject.toml           # uv 依赖管理
│
├── deploy/                      # 部署配置
│   ├── docker-compose.server.yml # Compose 服务定义
│   ├── nginx/                   # nginx 配置
│   ├── scripts/                 # 部署和运维脚本
│   │   ├── deploy-release.sh    # 服务器端发布脚本
│   │   ├── init-server.sh       # 服务器初始化
│   │   ├── install-docker.sh    # Docker 安装
│   │   ├── app-cli.sh           # 应用 CLI 包装
│   │   ├── docker-cleanup.sh    # 镜像清理
│   │   └── lib/                 # 部署公共函数
│   └── server.env.example       # 服务器环境配置模板
│
├── scripts/                     # 开发工作站脚本
│   ├── check.sh                 # 统一检查入口
│   ├── deploy.sh                # 触发远端部署
│   ├── status.sh                # 状态和日志查看
│   └── db.sh                    # 数据库备份和恢复
│
└── docs/                        # 文档
    ├── spec/                    # 功能规格
    ├── adr/                     # 架构决策记录
    └── runbook/                 # 运维手册
```

构建方式：
- 前端：`pnpm` 管理依赖；Docker 构建时 Node.js 编译为静态文件，产物拷入 nginx 镜像。
- 后端：`uv` 管理依赖；Docker 构建时安装 Python 依赖，同一镜像用于 backend、worker 和 bot 三个进程。
- 数据库迁移：Alembic 管理迁移脚本，部署时执行 `alembic upgrade head`。

### 3.4、部署视图

```text
┌──────────────────────────────────────────────────────────────┐
│              服务器 (openEuler 24.03 aarch64)                  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │            Docker Compose (kronos-dev)                  │  │
│  │                                                        │  │
│  │  nginx :8080 ─── 反向代理 /api/ → backend:8000          │  │
│  │    │                                                   │  │
│  │    ▼                                                   │  │
│  │  backend (FastAPI) ── postgres ── redis                │  │
│  │    │                                      │            │  │
│  │    │  ┌──────────────────────────────────┘            │  │
│  │    │  │                                                │  │
│  │    ▼  ▼                                                │  │
│  │  worker (Celery)    bot (飞书长连接)                    │  │
│  │                                                        │  │
│  │  卷: postgres_data (命名卷)                             │  │
│  │  挂载: /etc/kronos/ssh → /etc/kronos/ssh:ro            │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │            Docker Compose (kronos-prod)                  │  │
│  │  nginx :80 ─── (同 dev 拓扑，独立数据库卷和 Secret)       │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                              │
│  /opt/kronos/dev/app/      # dev Git 工作树                   │
│  /opt/kronos/prod/app/     # prod Git 工作树                  │
│  /etc/kronos/dev.env       # dev 配置 (权限 600)              │
│  /etc/kronos/prod.env      # prod 配置 (权限 600)             │
│  /etc/kronos/ssh/id_rsa    # VM 宿主登录私钥 (权限 600)        │
│  /data/backups/kronos/prod/ # prod 数据库备份                 │
└──────────────────────────────────────────────────────────────┘
```

dev 和 prod 使用独立 Compose 项目名，独立数据库卷、网络和配置文件。只有 nginx 暴露宿主端口。

备份策略：
- prod 部署前自动备份 PostgreSQL 到 `/data/backups/kronos/prod/<时间>-<commit>.dump`。
- 手工备份通过 `./scripts/db.sh backup prod`。
- 自动部署备份超过 30 天自动清理；`manual-*` 手工备份不被自动清理。
- 不配置每日定时备份。

### 3.5、运行视图

关键服务运行时的动态交互：

```text
┌─────────── 浏览器请求 ───────────┐

浏览器 ──HTTP──▶ nginx :8080
                    │
                    ├── 静态文件? ──▶ 返回前端 HTML/JS/CSS
                    │
                    └── /api/* ? ──▶ backend :8000
                                      │
                                      ├── JWT 校验 (core/security.py)
                                      ├── get_db 依赖 (db/session.py)
                                      │
                                      ├── 读操作 ──▶ PostgreSQL (同步 Session)
                                      │              │
                                      │              └── 返回 JSON
                                      │
                                      ├── 写操作 ──▶ service 层
                                      │              ├── 事务 + 行锁
                                      │              ├── 幂等检查 (idempotency/)
                                      │              ├── 审计写入 (audit/)
                                      │              └── 提交事务
                                      │
                                      └── VM 电源? ──▶ process_runner
                                                       └── ssh root@宿主 virsh ...
                                                           (同步，不写任务事件)

┌─────────── 异步任务 ───────────┐

backend ──Celery──▶ Redis ──▶ worker
                               │
                               ├── VM 创建任务:
                               │   1. 宿主选择 (tags=vm-host, arch, active, idle)
                               │   2. SSH 登录宿主 (/etc/kronos/ssh/id_rsa)
                               │   3. 执行 host_scripts/ 脚本
                               │   4. 增量写入 TaskEvent
                               │   5. 写入虚拟资源 + 租约
                               │   6. 更新 VMRequest.status
                               │
                               ├── VM 销毁任务:
                               │   1. SSH 登录宿主
                               │   2. 执行销毁脚本
                               │   3. 成功后释放租约 + 软删除资源
                               │
                               └── 测试任务:
                                   1. 同步 Mugen 用例索引
                                   2. 按 env_set_num 创建 N 套环境
                                   3. 每套: 申请 VM → 部署 Mugen → 执行 case
                                   4. 记录 TestCaseRun (exit_code)
                                   5. 销毁 VM (除非 keep_failed_env)

┌─────────── 飞书 Bot ───────────┐

飞书 ──长连接──▶ bot 进程
                   │
                   ├── 私聊命令 (help/资源查询)
                   │   └── 查 PostgreSQL → 返回卡片
                   │
                   ├── 卡片交互 (VM 申请)
                   │   └── 写 PostgreSQL → 发 Celery 任务
                   │
                   └── 远程命令
                       └── 查资源凭据 (Fernet 解密)
                           └── SSH 执行命令 → 返回输出到飞书
                           └── 写审计日志
```

### 3.6、质量属性设计

#### 3.6.1、性能规格

| 规格名称 | 规格指标 |
| --- | --- |
| API 响应时间 | 常规读写 API 在 1 秒内返回 |
| VM 电源操作 | 同步 `virsh` 执行，通常 5 秒内完成 |
| VM 创建 | 异步，通常 5-15 分钟完成（取决于镜像下载） |
| 测试任务超时 | 创建后 8 小时 |
| VM 创建超时 | 60 分钟后懒判断标记失败 |
| Worker 并发 | dev 2 个，prod 4 个 |
| Worker 预取 | `prefetch-multiplier=1`，一次只领一个任务 |
| 容器停止宽限期 | worker 20 分钟（`stop_grace_period: 20m`） |
| 日志轮转 | 每容器最多 5 个 10MB 文件（`json-file`） |
| 任务事件保留 | 30 天自动清理 |
| 幂等记录保留 | 7 天自动清理 |

#### 3.6.2、系统可靠性设计

- **租约并发安全**：PostgreSQL 部分唯一索引保证每资源同一时间只有一个活跃租约；操作使用 `lease_id` 避免旧请求影响下一任租约。
- **幂等写接口**：关键写操作使用 `Idempotency-Key` + 请求哈希去重，客户端可安全重试。
- **部署锁**：`flock` 文件锁防止同一环境并发部署。
- **存储空间预检**：部署前检查 `/`、`/data`、DockerRootDir 和 PostgreSQL 卷空间，任一低于 10GB 或使用率超 90% 中止部署。
- **数据库备份**：prod 部署前自动备份；恢复脚本要求输入完整环境名确认。
- **容器重启策略**：所有服务 `restart: unless-stopped`。
- **VM 创建回滚**：宿主脚本尽量保证全成或全退；回滚失败时申请单标记失败并提示管理员处理。
- **不自动回滚**：发布脚本不自动回滚应用或数据库；回滚优先用 Git revert + 重新部署。

#### 3.6.3、安全性设计

- **认证**：本地账号 + JWT (HS256, 1 天有效期)；PAT 规划中（明文只展示一次，DB 存哈希）。
- **凭据加密**：SSH/BMC 凭据使用 Fernet 应用层加密存储。
- **凭据查看**：独立后端 API + 后端鉴权；不记录查看行为；修改写审计日志。
- **角色权限**：`ADMIN`/`TSE`/`TE` 三角色；后端鉴权为最终边界；关键资源凭据只能 `ADMIN` 查看。
- **审计覆盖**：登录、用户管理、资源变更、凭据修改、导入导出和远程命令执行。
- **Secret 隔离**：dev/prod 使用不同数据库密码、JWT 密钥和 Fernet 密钥；真实 Secret 只在 `/etc/kronos/*.env` (权限 600)。
- **飞书身份绑定**：只用于 Bot 识别操作者，不作为 Web 登录或 SSO；不通过飞书扫码自动创建用户。
- **禁用用户**：令牌立即失效（每次请求校验 `is_active`）。

#### 3.6.4、兼容性设计

- 服务器操作系统：openEuler 24.03 (LTS-SP4)，aarch64 架构。
- 数据库迁移：Alembic 增量迁移，不自动 downgrade。
- 前端浏览器：现代浏览器（Chrome/Edge/Firefox），需要 WebSocket 支持（VNC 控制台）。
- VM 宿主机：openEuler，需预装 libvirt/virsh/virt-install/qemu-img。
- Docker 镜像加速：国内网络可能需要配置 `/etc/docker/daemon.json` registry-mirrors。

#### 3.6.5、可服务性设计

- **状态和日志**：`./scripts/status.sh <env>` 展示磁盘空间、Docker 资源占用和表大小估算；`--logs` 查看容器日志。
- **部署历史**：`/opt/kronos/<env>/deployments.jsonl` 记录每次部署的分支、commit、操作者和结果。
- **最后成功版本**：`/opt/kronos/<env>/deployed-commit` 记录最后成功部署的 commit。
- **手动清理**：`app-cli.sh <env> cleanup-task-events --days 30` 和 `cleanup-idempotency-records --days 7`。
- **数据库备份恢复**：`./scripts/db.sh backup/restore prod`。
- **镜像清理**：`docker-cleanup.sh --dry-run/--run`，每仓库每环境保留最新 2 个镜像。
- **应急资源导入**：`app-cli.sh <env> upsert-resource --json-file`。
- **管理员创建**：`app-cli.sh <env> create-admin`，密码交互输入。

#### 3.6.6、可测试性设计

- **统一检查入口**：`./scripts/check.sh all` 执行 lint、typecheck 和测试。
- **隔离测试数据**：自动化测试不连接 `kronos_dev` 或 `kronos_prod`；通过 `TEST_DATABASE_URL` 指向独立测试库 `kronos_test`。
- **不部署 test 网站**：`test` 不是独立部署环境，只用于自动化测试。
- **OpenAPI 文档**：FastAPI 自动生成 OpenAPI 文档，作为 API 契约。

### 3.7、特性清单

| no | 特性描述 | 代码估计规模 | 实现版本 |
| --- | --- | --- | --- |
| F-01 | 本地账号登录、JWT、用户模型、用户管理 API 和创建管理员 CLI | 中 | 已交付 |
| F-02 | 资源台账数据库表、资源 API 和资源 upsert CLI | 中 | 已交付 |
| F-03 | 资源占用、续期、释放、强制释放、懒释放 | 中 | 已交付 |
| F-04 | 授权凭据查看（Fernet 加解密 + 后端鉴权） | 小 | 已交付 |
| F-05 | 资源 CSV 导入导出、租约 CSV 导入 | 中 | 已交付 |
| F-06 | VM 申请、申请记录、异步创建、异步释放和任务事件 | 大 | 已交付 |
| F-07 | VM Web VNC 控制台和 VM 电源操作 | 中 | 已交付 |
| F-08 | 飞书应用配置 API 和管理页面、Bot 长连接、Web 账号绑定、私聊卡片交互 | 大 | 已交付 |
| F-09 | 测试管理模型、Mugen 用例索引同步、测试用例与任务页面 | 大 | 已交付 |
| F-10 | VM 测试任务执行 worker | 大 | 已交付 |
| F-11 | 审计日志写入和 ADMIN 审计页面 | 小 | 已交付 |
| F-12 | 按角色可见的租约事件页面 | 小 | 已交付 |
| F-13 | PAT（个人访问令牌） | 小 | 不支持 |
| F-14 | 测试任务真实 VM 环境联调 | — | 不支持 |
| F-15 | 资源池、XLSX 导入和连通性检查 | 中 | 不支持 |
| F-16 | 流水线编排层（Pipeline Type 注册 / Pipeline / Run / RunJob / 模块模板） | 大 | 已交付 |
| F-17 | pkgcmd/pkgserver repodata 解析和 env_type 拆分 | 中 | 已交付 |
| F-18 | 物理机执行模式（自动选择资源+租约占用） | 中 | 已交付 |
| F-19 | VM 挂死检测和 virsh console 诊断 | 中 | 已交付 |
| F-20 | 子用例结果解析（LTP/Mugen results） | 中 | 已交付 |
| F-21 | 日志收集和共享卷存储 | 小 | 已交付 |
| F-22 | 流水线 Web UI 看板（矩阵+下钻） | 中 | 已交付 |
| F-23 | 各模块 pre/post env_script 脚本和端到端联调 | 大 | 不支持 |
| F-24 | 流水线类型管理（前端可增删 B 类 direct_run 类型，含 release 类型 seed） | 中 | 不支持 |
| F-25 | 配置删除与历史执行汇集（含 per-config 历史页 + 全局近期执行 feed） | 中 | 不支持 |
| F-26 | 测试模块模板按类型划分 + `mugen_suite` 改名 `suite_name` | 中 | 不支持 |
| F-27 | VM 镜像发现双源（iteration + official）+ os_version 带 dist 前缀 | 中 | 不支持 |
| F-28 | 流水线执行链路修复（GSSAPI 跳过 + mugen 前置依赖 + 状态 read-time + 日志汇集 + SSH 重试日志） | 中 | 不支持 |
| F-29 | 流水线 UI 改进（页签命名 + RunJob 重构 + 自动刷新 + 换源脚本） | 中 | 不支持 |

### 3.8、接口清单

#### 3.8.1、外部接口清单

| 接口名称 | 接口描述 | 入参 | 输出 | 异常 |
| --- | --- | --- | --- | --- |
| POST /api/v1/auth/login | 登录并获取 JWT | `username`, `password` | `access_token`, `token_type` | 401 用户名或密码错误 |
| GET /api/v1/auth/me | 获取当前用户信息 | Bearer token | `id`, `username`, `role`, `display_name` | 401 未认证 |
| GET /api/v1/users | 用户列表 | Bearer token (ADMIN) | `User[]` | 403 非管理员 |
| POST /api/v1/users | 创建用户 | `username`, `password`, `role`, `display_name` | `User` | 409 用户名已存在 |
| GET /api/v1/resources | 资源列表 | Bearer token, 查询参数 | `Resource[]` (分页) | 401 未认证 |
| POST /api/v1/resources | 创建资源 | Bearer token (ADMIN/TSE), 资源 JSON | `Resource` | 403 无权限 |
| GET /api/v1/resources/{id}/credentials | 查看凭据 | Bearer token | `{ssh_username, ssh_password, ...}` | 403 无权限查看 |
| POST /api/v1/resources/{id}/lease | 占用资源 | Bearer token, `purpose`, `expected_ends_at`, `Idempotency-Key` | `Lease` | 409 资源已占用 |
| DELETE /api/v1/leases/{id} | 释放租约 | Bearer token, `Idempotency-Key` | 204 | 403 非租约所有者 |
| POST /api/v1/leases/{id}/extend | 续期 | Bearer token, `Idempotency-Key` | `Lease` | 409 超过续期上限 |
| GET /api/v1/vm/images | VM 镜像列表 | Bearer token | `Image[]` | 502 镜像仓库不可达 |
| POST /api/v1/vm/requests | 申请 VM | Bearer token, 规格参数, `Idempotency-Key` | `VMRequest` | 422 参数校验失败 |
| DELETE /api/v1/vm/requests/{id} | 取消 VM 申请 | Bearer token | 204 | 409 已进入 creating |
| POST /api/v1/vms/{id}/power | VM 电源操作 | Bearer token, `action` (start/stop/restart) | `power_state` | 502 宿主机不可达 |
| GET /api/v1/test/cases | Mugen 用例列表 | Bearer token, 查询参数 | `MugenCase[]` (分页) | — |
| POST /api/v1/test/jobs | 创建测试任务 | Bearer token, 任务参数 | `TestJob` | 422 参数校验失败 |
| GET /api/v1/test/jobs/{id} | 测试任务详情 | Bearer token | `TestJob` (含 env_sets, case_runs) | 404 不存在 |
| GET /api/v1/lease-events | 租约事件 | Bearer token, 查询参数 | `LeaseEvent[]` (分页) | — |
| GET /api/v1/audit-logs | 审计日志 | Bearer token (ADMIN) | `AuditLog[]` (分页) | 403 非管理员 |
| GET /api/v1/integrations/feishu/oauth/callback | 飞书 OAuth 回调 | `code` | 重定向 | 400 回调参数无效 |
| GET /api/v1/pipelines/module-templates | 模块模板列表 | Bearer token | `TestModuleTemplate[]` | — |
| PUT /api/v1/pipelines/module-templates/{id} | 更新模块模板 | Bearer token (ADMIN), 模板字段 | `TestModuleTemplate` | 404 模板不存在 |
| GET /api/v1/pipelines/types | 流水线类型列表 | Bearer token | `PipelineType[]` | — |
| POST /api/v1/pipelines/types | 创建流水线类型（B 类 direct_run） | Bearer token (ADMIN), 类型字段 | `PipelineType` | 409 名称已存在 |
| DELETE /api/v1/pipelines/types/{id} | 删除流水线类型 | Bearer token (ADMIN) | 204 | 403 系统类型不可删 / 409 有引用 |
| GET /api/v1/pipelines/frameworks | 测试框架列表（代码注册） | Bearer token | `Framework[]` | — |
| GET /api/v1/pipelines/configs | Pipeline 配置列表 | Bearer token | `PipelineConfig[]` | — |
| POST /api/v1/pipelines/configs | 创建 Pipeline 配置 | Bearer token (ADMIN), 配置 JSON | `PipelineConfig` | — |
| PUT /api/v1/pipelines/configs/{id} | 更新配置（版本列表等） | Bearer token (ADMIN), 字段 | `PipelineConfig` | 404 配置不存在 |
| POST /api/v1/pipelines/trigger | 触发流水线 | Bearer token (ADMIN), `config_id`, 可选 `versions`/`archs`/`image_round` | `PipelineExecution` | 404 配置不存在 |
| GET /api/v1/pipelines/executions | Pipeline Execution 列表 | Bearer token | `PipelineExecution[]` | — |
| GET /api/v1/pipelines/executions/{id}/summary | Execution 看板汇总 | Bearer token | summary JSON | 404 不存在 |
| POST /api/v1/pipelines/executions/{id}/destroy-envs | 销毁保留环境 | Bearer token (ADMIN) | 204 | 404 不存在 |
| GET /api/v1/pipelines/runs | Pipeline Run 列表 | Bearer token | `PipelineRun[]` | — |
| GET /api/v1/pipelines/runs/{id} | Run 详情 | Bearer token | `PipelineRun` | 404 Run 不存在 |
| GET /api/v1/pipelines/runs/{id}/jobs | Run 的模块×架构 Job 列表 | Bearer token | `PipelineRunJob[]` | — |
| GET /api/v1/pipelines/run-jobs/{id} | RunJob 详情 | Bearer token | `PipelineRunJob` 详情 | 404 不存在 |
| GET /api/v1/pipelines/runs/{id}/logs | 日志列表 | Bearer token | `TestLogArtifact[]` | — |
| GET /api/v1/pipelines/runs/{id}/logs/{artifact_id} | 日志内容 | Bearer token | 文本（超 1MB 截断） | 404 不存在 |

#### 3.8.2、内部接口清单

| 模块 | 接口名称 | 接口描述 | 入参 | 输出 | 异常 |
| --- | --- | --- | --- | --- | --- |
| core/security | `create_access_token(subject)` | 签发 JWT | `user_id` | JWT 字符串 | — |
| core/security | `get_current_user(token, db)` | 从 JWT 解析当前用户 | Bearer token, Session | `User` | 401 令牌无效或用户禁用 |
| core/credentials | `encrypt_secret(value)` | Fernet 加密凭据 | 明文 | 密文字符串 | — |
| core/credentials | `decrypt_secret(value)` | Fernet 解密凭据 | 密文 | 明文字符串 | — |
| core/process_runner | `run(...)` | 同步执行外部进程 (virsh/ssh) | 命令参数 | stdout/stderr/exit_code | 超时或执行失败 |
| modules/leases/service | `occupy_resource(db, resource_id, user, ...)` | 占用资源并创建租约 | Session, resource_id, User, purpose | `ResourceLease` | 409 资源已占用 |
| modules/leases/service | `release_lease(db, lease_id, user, ...)` | 释放租约 | Session, lease_id, User | — | 403 非租约所有者 |
| modules/vms/service | `create_vm_request(db, user, ...)` | 创建 VM 申请 | Session, User, 规格参数 | `VMRequest` | 422 参数校验失败 |
| modules/vms/tasks | `create_vm_task(vm_request_id)` | Celery 任务：VM 异步创建 | `vm_request_id` | — | 任务失败时更新状态 |
| modules/vms/tasks | `destroy_vm_task(resource_id)` | Celery 任务：VM 异步销毁 | `resource_id` | — | 销毁失败时保持租约 |
| modules/vms/image_discovery | `discover_images()` | 从镜像仓库解析可用镜像 | — | `Image[]` | 502 仓库不可达 |
| modules/vms/host_runner | `run_host_script(host, script, ...)` | SSH 到宿主机执行脚本 | 宿主 IP, 脚本路径, 参数 | 脚本输出 | SSH 或脚本失败 |
| modules/test_management/tasks | `run_test_job(job_id)` | Celery 任务：测试任务执行 | `job_id` | — | 任务异常时更新状态 |
| modules/test_management/execution | `execute_case(env_set, case)` | 在环境套中执行单个用例 | TestEnvSet, MugenCase | exit_code, stdout_summary | 超时由 `CASE_TIMEOUT_SECONDS` 控制（默认 7 小时） |
| modules/audit/service | `write_audit(db, actor, action, target, detail)` | 写审计日志 | Session, User, action, target | `AuditLog` | — |
| modules/tasks/service | `write_task_event(...)` | 写任务事件 | task_type, subject, phase, message | `TaskEvent` | — |
| modules/idempotency/service | `check_and_store(...)` | 幂等键去重 | key, user, method, path, hash | 首次响应或冲突错误 | 409 幂等冲突 |
| modules/feishu/commands | `handle_command(message)` | 处理飞书私聊命令 | 飞书消息事件 | 卡片 JSON | — |
| modules/feishu/remote_command | `execute(user, resource, command)` | 飞书远程命令执行 | User, Resource, 命令字符串 | 命令输出 | SSH 失败 |

---

## 4、修改日志

| 版本 | 发布说明 |
| --- | --- |
| 初始版本 | 资源台账、租约管理、凭据保护、VM 申请/释放、Web VNC、飞书 Bot、Mugen 测试任务、审计日志、租约事件 |
| Update 流水线 | Pipeline 编排层、模块模板、repodata 解析、物理机执行、挂死检测、子用例解析、日志收集、Web UI 看板 |
| 流水线类型注册 | `pipeline_types` 表、A 类代码驱动 / B 类数据驱动拆分、`DirectRunPipelineStrategy`、release 类型 seed、`image_round` 双层归属、前端类型管理页 |
| 配置删除与历史汇集 | 硬删 + 有引用拒删、单条/批量删 execution 接口、per-config 历史页 `/pipelines/configs/:id/executions`、全局"近期执行" feed 限 20 条 |
| 模板按类型划分 + 字段改名 | `TestModuleTemplate.pipeline_type` 字段、`mugen_suite` → `suite_name`、UI 按 type segmented filter |
| VM 镜像发现双源 + 版本前缀 | iteration + official 双源解析、os_version 带 `<dist>-` 前缀（支持多 OS）、official 镜像标 `image_round="official"` |
| 流水线执行链路修复 | GSSAPI 跳过 SSH 挂起、mugen 部署前装 git/python3-pip、`db.commit()` 在 `process_test_job` 前提交 TestJob、Run/Execution 状态 read-time worst-wins 推算、日志汇集从 `run_job.test_job_id` 获取 TestJob、SSH 重试日志（每 30s 记 task event）、SSH 超时 15 分钟 |
| 流水线 UI 改进 | 页签动态命名（路由 title 区分）、RunJob 详情重构（删子用例+加统计卡片+内联执行结果+折叠时间线）、execution-detail 10s 自动刷新、公共换源脚本 `UPDATE_REPO_SETUP` 嵌入所有 update 模块 |

---

## 5、参考目录

- [CONTEXT.md](../CONTEXT.md)：领域语言、角色、状态模型和核心规则
- [资源管理功能规格](spec/0001-resource-management.md)：资源管理行为、页面、API 和验收标准
- [测试管理功能规格](spec/0002-test-management.md)：Mugen 用例同步、VM 测试任务、环境套和 case 结果规则
- [ADR 0001：技术栈(Technology Stack)](adr/0001-tech-stack.md)：前端(Frontend)：Vue 3、TypeScript、Vben Admin、Ant Design Vue
- [ADR 0002：资源模型(Resource Model)](adr/0002-resource-model.md)：内部主键(Primary Key)：id，类型为 UUID
- [ADR 0003：认证、权限和凭据(Authentication, Authorization, Credentials)](adr/0003-auth-permission.md)：只支持本地账号(Local Account)
- [ADR 0004：部署和开发流程(Deployment and Development Workflow)](adr/0004-deployment-and-dev-workflow.md)：radiaTest 在单台 openEuler 服务器上开发和部署
- [ADR 0005：VM 生命周期和异步执行(VM Lifecycle and Async Execution)](adr/0005-vm-lifecycle-and-async-execution.md)：API 创建 VM 申请单后立即返回
- [ADR 0006：飞书 Bot 和身份绑定(Feishu Bot and Identity Binding)](adr/0006-feishu-bot-and-identity-binding.md)：支持飞书 Bot 作为 IM 集成(Instant Messaging Integration)
- [ADR 0007：测试管理和 Mugen 执行(Test Management and Mugen Execution)](adr/0007-test-management-and-mugen-execution.md)：测试任务(Test Job)独立建模，不升级或复用远程命令(Remote Command)作为产品概念
- [ADR 0008：统一服务端分页契约](adr/0008-server-side-pagination.md)：列表请求统一使用从 1 开始的 page，每页固定 50 条
- [ADR 0009：通知投递和定时提醒](adr/0009-notification-delivery-and-scheduling.md)：PostgreSQL 中的站内通知是唯一事实来源
- [ADR 0010：流水线类型注册——数据驱动 vs 代码驱动](adr/0010-pipeline-type-registration-data-vs-code.md)：A 类（代码驱动）：含复杂编排逻辑（如 update 的模块矩阵 + repodata 包筛选 + env_type_split）
- [ADR 0011：流水线配置删除与历史执行汇集](adr/0011-pipeline-config-delete-and-execution-history.md)：DELETE /pipelines/executions/{id} —— 删单个 execution（级联 runs/run_jobs）
- [ADR 0012：测试模块模板按类型划分与 `mugen_suite` 改名](adr/0012-test-module-template-pipeline-type-and-suite-rename.md)：update 的 5 个 seed 模板 pipeline_type="update"
- [ADR 0013：VM 镜像发现双源解析与版本号带 dist 前缀](adr/0013-vm-image-discovery-dual-source-and-version-prefix.md)：iteration：os_version = version_dir（已经是 openEuler-24.03-LTS-SP3 形式）
- [ADR 0014：物理机 PXE 安装](adr/0014-physical-machine-pxe-install.md)：POST /resources/{id}/install API + 异步 Celery 任务编排 5 步装机流程
- [ADR 0015：update 流水线 kernel 模块——env_type 模型 + 物理机重装集成 + 按 result_parser 派发展示](adr/0015-kernel-module-envtype-physical-reinstall-result-dispatch.md)：both → 一个 RunJob，TestJob 内创建 VM/physical EnvSet（ADR 0018 取代了本文早期的双 RunJob 方案）
- [ADR 0016：HangDetector 从"不可逆判死"改为"可自愈（非对称 3-set/1-clear）"](adr/0016-hang-detector-self-heal.md)：5 次连续失败才 set（max_failures=3→5，2026-08-15 调宽）——高负载 VM（如 sssd 测试期间）sshd 响应慢，3 次 10
- [ADR 0017：模块日志收集路径 /opt/<module>-logs + pkgcmd 结果展示](adr/0017-module-log-path-pkgcmd-display.md)：docker → /opt/docker-logs/
- [ADR 0018：env_type=both 合并为单 RunJob + 动态 env_set + update_list 早展示 + suite 级折叠](adr/0018-both-single-runjob-dynamic-envset-updatelist-suite-collapse.md)：有 vm_cases → 建 VM env_set，node_num = max(vm_cases 的 node_num)
- [ADR 0019：pkgcmd.log per-case 收集 + suite 级折叠 + update_list 先展示](adr/0019-pkgcmd-log-percase-suite-collapse-updatelist-first.md)：run_case 跑完 mugen.sh -f <suite> -r <case> -x 后，立刻 SSH 执行一段统计脚本，输出追加到 pkgcmd.log
- [ADR 0020：mugen_runner SSH 跳过 host key 验证 + 节点跳转按 env_type + 部署树前端同步](adr/0020-ssh-verify-host-key-deploy-tree-frontend-sync.md)：1. run_remote_bash_command 加 verify_host_key 参数
- [ADR 0021：pkgcmd 隐藏右栏 + case 跳转 mugen 日志 + 前端去 emoji](adr/0021-pkgcmd-hide-rightcard-case-mugenlog-no-emoji.md)：1. pkgcmd 隐藏右栏
- [ADR 0022：pkgserver 执行逻辑重做 — repodata 发现 + builder 调度](adr/0022-pkgserver-dispatch-from-preenv.md)：调 fetch_service_packages(repo_base_url, version, arch) 解析 update 仓库 binary repo
- [ADR 0023：pkgcmd/pkgserver 的 physical env_set 复用 kernel 物理机（隐式锁 + 前序链查找 + fallback）](adr/0023-pkgcmd-pkgserver-physical-reuse-kernel-machine.md)：pkgcmd 前序链：[kernel]
- [ADR 0024：VM/物理机/流水线 64k 内核后处理](adr/0024-vm-64k-kernel-post-processing.md)：VM（apply_kernel_64k）：record_vm_request_event（subject_type=vm_request）
- [ADR 0025：流水线 VM 创建按宿主机并发控制](adr/0025-vm-create-per-host-serialization.md)：Celery 的 ForkPoolWorker 是 fork 出来的独立进程，threading.Lock 跨不了进程
- [ADR 0026：kernel 模块物理机装最新 update 内核](adr/0026-kernel-module-latest-update-kernel.md)：1. kernel 模块物理机新增"装最新 update 内核"步骤
- [ADR 0027：RunJob 失败用例按选重跑](adr/0027-rerun-selected-pipeline-cases.md)：已登录用户可在终态 Pipeline RunJob 中选择失败的 Mugen Case Run 重跑
- [ADR 0028：在来源环境中按选重跑 RunJob 用例](adr/0028-rerun-cases-in-source-environment.md)：已登录用户只能从重跑链上最新的终态 RunJob 发起用例重跑
- [ADR 0029：物理机测试占用由执行事实派生并用于调度](adr/0029-physical-test-resource-usage-state.md)：管理状态、租约状态与测试状态保持独立：management_status 继续表达资源是否可管理，
- [ADR 0030：RunJob 取消功能](adr/0030-runjob-cancel.md)：状态机
- [ADR 0031：TestJob/RunJob 终止收敛机制（本地 kill + 分级终止信号）](adr/0031-termination-convergence.md)：_run_env_set_thread 捕获 TestJobExecutionError(code="job_cancelled")
- [ADR 0032：Update 测试流水线](adr/0032-update-test-pipeline.md)：1. Pipeline 作为 TestJob 之上的编排层
- [ADR 0033：Update 测试流水线执行模型](adr/0033-update-pipeline-execution-model.md)：同步扁平——web 里同步拉 repodata 建所有 TestJob 再派发，任一版本 repodata 失败整次触发失败，web 干网络活
- [ADR 0034：API 错误契约和请求追踪](adr/0034-api-error-contract-and-request-tracing.md)：所有 /api/v1 JSON 错误统一使用包含 code、message 和可选 details
- [ADR 0035：Worker 中断恢复](adr/0035-worker-interruption-recovery.md)：保持 Celery 默认的执行前消息确认，不启用 acks_late 或
- [ADR 0036：Test Job 与 Pipeline 的单向模块边界](adr/0036-test-job-pipeline-one-way-seam.md)：依赖方向固定为 Pipeline → Test Job
- [ADR 0037：run-job 统计与用例列表展示语义细化](adr/0037-runjob-stats-and-suite-header-display.md)：用例行：总计 / 通过 / 失败（常显）
- [Update 测试流水线实现计划](plans/completed/update-test-pipeline.md)：10 个 Task 的实现进度和验收标准
- [流水线类型注册实现计划](plans/completed/pipeline-type-registration.md)：问题 1 的 8 个 Task 实现进度
- [配置删除与历史执行汇集实现计划](plans/completed/pipeline-config-delete-and-execution-history.md)：问题 2 的 6 个 Task 实现进度
- [服务器部署运行手册](runbook/server-deployment.md)：远程 dev/prod 发布、备份、权限和故障处理约定
- [AGENTS.md](../AGENTS.md)：AI Agent 在本项目中的协作规则
