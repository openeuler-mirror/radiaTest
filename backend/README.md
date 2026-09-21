<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# radiaTest 后端

radiaTest 后端使用 FastAPI、SQLAlchemy、Alembic 和 PostgreSQL。

## 开发方式

后端只在远程 Linux `dev` 环境运行。开发工作站修改代码并推送到 GitCode 后，
在服务器 `/opt/kronos/dev/app` 执行 `./scripts/deploy.sh [分支名]` 部署并验证。

## 检查命令

```bash
uv sync
uv run ruff check app tests alembic
uv run pytest
```

## API

API 统一挂载在：

```text
/api/v1
```

可用接口：

```text
GET /api/v1/health
GET /api/v1/health/database
POST /api/v1/auth/login
GET /api/v1/users/me
POST /api/v1/users/me/change-password
GET /api/v1/users
POST /api/v1/users
PATCH /api/v1/users/{user_id}
POST /api/v1/users/{user_id}/reset-password
GET /api/v1/integrations/feishu/app
PUT /api/v1/integrations/feishu/app
GET /api/v1/integrations/feishu/me/identity
GET /api/v1/integrations/feishu/me/bind-url
GET /api/v1/integrations/feishu/oauth/callback
GET /api/v1/resources
POST /api/v1/resources
POST /api/v1/resources/imports
GET /api/v1/resources/exports
GET /api/v1/resources/{id}
PATCH /api/v1/resources/{id}
POST /api/v1/resources/{resource_id}/leases
GET /api/v1/resources/{resource_id}/credentials
POST /api/v1/leases/imports
POST /api/v1/leases/{lease_id}/extend
POST /api/v1/leases/{lease_id}/release
POST /api/v1/leases/{lease_id}/force-release
GET /api/v1/lease-events
GET /api/v1/vm-images
POST /api/v1/vm-isos
POST /api/v1/vm-requests
GET /api/v1/vm-requests
POST /api/v1/vm-requests/{request_id}/cancel
GET /api/v1/vm-requests/{request_id}/events
GET /api/v1/vms
GET /api/v1/vms/{resource_id}/console
GET /api/v1/vms/{resource_id}/power
POST /api/v1/vms/{resource_id}/power
GET /api/v1/vms/{resource_id}/events
POST /api/v1/vms/{resource_id}/refresh-ip
POST /api/v1/vms/{resource_id}/release
GET /api/v1/test-cases
POST /api/v1/test-cases/sync
GET /api/v1/test-cases/sync/events
POST /api/v1/test-jobs
GET /api/v1/test-jobs
GET /api/v1/test-jobs/{job_id}
GET /api/v1/test-jobs/{job_id}/events
GET /api/v1/test-job-templates
POST /api/v1/test-job-templates
GET /api/v1/test-job-templates/{template_id}
PATCH /api/v1/test-job-templates/{template_id}
DELETE /api/v1/test-job-templates/{template_id}
GET /api/v1/tickets
POST /api/v1/tickets
GET /api/v1/tickets/{ticket_id}
PATCH /api/v1/tickets/{ticket_id}
POST /api/v1/tickets/{ticket_id}/accept
POST /api/v1/tickets/{ticket_id}/reject
PATCH /api/v1/tickets/{ticket_id}/handling
POST /api/v1/tickets/{ticket_id}/complete
POST /api/v1/tickets/{ticket_id}/comments
GET /api/v1/notifications
GET /api/v1/notifications/unread-count
PATCH /api/v1/notifications/{notification_id}/read
POST /api/v1/notifications/read-all
GET /api/v1/audit-logs
```

用户管理接口仅 `ADMIN` 可用。创建、修改、重置密码会写审计日志，审计详情不包含密码。

资源列表支持 `match=and|or` 和逐列文本模糊过滤。常用过滤字段包括 OS IP、
BMC IP、架构、CPU、显示名、资源编码、MAC、OS、内核、管理状态、占用状态、
占用人、占用用途和使用场景。资源列表默认按 OS IP 自然排序，例如
`172.168.131.9` 排在 `172.168.131.10` 前面。示例：

```text
GET /api/v1/resources?match=and&primary_ip=172.168.&cpu_model=Intel
```

资源读取接口不返回密码明文，只返回 `has_ssh_password` 和 `has_bmc_password`。
凭据明文通过独立凭据接口查看，不记录查看日志。资源更新接口可以修改资源台账字段和
凭据字段，审计详情只记录字段名，不记录密码明文。占用、续期、释放、强制释放、导入确认、
VM 申请、VM 释放、VM 电源操作和测试任务创建接口必须携带 `Idempotency-Key` 请求头。VM 创建和销毁由
Celery worker 异步执行，API 返回申请单或已入队状态。VM 任务事件接口返回脱敏事件时间线，
用于定位创建或销毁卡住的阶段；VM 软删除后仍可读取保留期内的销毁事件。租约日志接口按
角色返回占用、续期、释放和自动释放记录。
VM 控制台配置接口返回 noVNC 所需的 WebSocket URL、传统 VNC 端口和 WebSocket 端口；
旧 VM 缺少 WebSocket 端口时返回 409。

本地 ISO 通过原始二进制请求体流式上传，不使用 multipart 临时文件。后端校验文件名、
`Content-Length`、实际字节数和存储空间，以 SHA-256 去重，并在上传中断时删除临时文件。

资源导出仅 `ADMIN` 可用，CSV 包含 SSH/BMC 密码明文，并写入不含密码明文的审计日志。

测试管理接口提供 Mugen suite/case 索引查询、`ADMIN` 手动同步、测试任务创建、
任务详情、任务事件和共享任务模板管理。模板接口不要求 `Idempotency-Key`；模板创建人和
`ADMIN` 可以修改或删除。测试任务执行细节以项目根目录的测试管理规格为准。

## 初始管理员

创建第一个管理员账号：

```bash
uv run python -m app.cli create-admin \
  --username admin \
  --display-name 管理员
```

如果不传 `--password`，命令会交互式输入密码。

## 资源和租约导入

日常数据迁移使用 Web 资源管理页的导入入口：

1. 导入资源 CSV。
2. 导入当前租约 CSV。
3. 导入前先校验，确认导入时后端要求 `Idempotency-Key`。

后端也提供同等能力：

```text
POST /api/v1/resources/imports
POST /api/v1/leases/imports
```

## 服务器侧资源维护

`upsert-resource` CLI 用于服务器侧应急或批量维护。通过 JSON 文件按
`resource_code` 创建或更新资源：

```bash
uv run python -m app.cli upsert-resource --json-file resources.json
```

也可以从标准输入读取：

```bash
uv run python -m app.cli upsert-resource --json-file - < resources.json
```

清理超过保留期的任务事件：

```bash
uv run python -m app.cli cleanup-task-events --days 30
```
