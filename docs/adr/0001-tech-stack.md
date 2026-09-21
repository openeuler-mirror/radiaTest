<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0001：技术栈(Technology Stack)

## 状态

已接受(Accepted)。

## 背景

radiaTest 需要交付一个可维护的内网管理平台。真正高风险的部分是资源身份、租约并发、权限、凭据处理、导入校验、审计和 API 契约。前端不应该重复造中后台基础设施，而应该复用成熟管理框架。

## 决策

采用：

- 前端(Frontend)：Vue 3、TypeScript、Vben Admin、Ant Design Vue。
- 前端包管理器(Package Manager)：pnpm，通过 Corepack 管理版本。
- 后端(Backend)：FastAPI。
- 持久化(Persistence)：PostgreSQL、SQLAlchemy 2.x 同步 ORM、Alembic。
- 异步任务(Async Task)：Celery worker 和 Redis。
- 后端包管理器：uv。
- API 风格：`/api/v1` 下的 REST API，并生成 OpenAPI 文档。
- 部署(Deployment)：Docker Compose，用于单台 Linux 服务器上的 `dev` 和 `prod` 环境。

## 理由

Vben Admin 提供成熟的 Vue 中后台外壳，包括登录、布局、菜单、权限、请求和常见管理页面模式。radiaTest 的核心页面是表格、筛选、表单、详情、弹窗和日志，Ant Design Vue 与这种中后台场景匹配。

FastAPI API 开发简单，并内置 OpenAPI 生成能力。选择同步 SQLAlchemy，是因为资源租约涉及事务、锁和状态变更，同步模型更容易推理。通过服务(Service)和仓储(Repository)边界，需要时仍然可以迁移到异步模型。

PostgreSQL 作为主数据库，因为 radiaTest 需要关系完整性、事务、行锁、JSONB、数组字段和可靠迁移。

Celery 和 Redis 用于执行 VM 创建、销毁等耗时任务。业务状态仍保存在 PostgreSQL，
Redis 只承担任务队列和结果后端职责。

## 影响

- Vben Admin 期望使用 pnpm。前端不能混用 npm、yarn、bun 和 pnpm。
- OpenAPI 由后端生成，并作为 API 契约。
- 数据库结构变更必须通过 Alembic。
- 前端权限检查只改善用户体验；后端鉴权才是最终权限边界。

## 备选方案

React + Ant Design Pro：

- 中后台生态强，ProTable 能力成熟。
- Umi 相关概念更多。
- 未选择，因为项目优先级是简单角色权限和快速中后台落地，Vue/Vben 路径更直接。

Vue + 自建 Vite 后台外壳：

- 控制力更高，也可以使用 npm。
- 需要自行搭建登录、布局、菜单、权限和管理约定。
- 未选择，因为前端外壳不是本项目的主要风险。
