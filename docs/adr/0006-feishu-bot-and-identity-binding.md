<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0006：飞书 Bot 和身份绑定(Feishu Bot and Identity Binding)

## 状态

已接受(Accepted)。

## 背景

radiaTest 需要通过飞书 Bot 提供移动端和 IM 场景下的资源查询能力。飞书 Bot 不是新的登录
入口，也不改变 radiaTest 的本地账号和角色模型；它只把飞书用户身份映射到已有 radiaTest
用户，再复用 radiaTest 当前权限规则执行查询。

## 决策

采用：

- 支持飞书 Bot 作为 IM 集成(Instant Messaging Integration)。
- 每套环境启用独立飞书应用和独立 Bot：`dev` 使用调试 Bot，`prod` 使用正式 Bot。
- `dev` 和 `prod` 不能共用同一个飞书 `app_id`。
- 飞书应用由 `ADMIN` 在飞书开放平台创建后配置，一套环境只需要配置一次。
- 飞书应用配置保存在当前环境数据库中，包括 `app_id`、`app_secret` 和启用状态。
- `app_secret` 按内网测试环境规则明文保存在数据库中，不提交到 Git。
- radiaTest 不实现飞书应用扫码创建或绑定向导；`ADMIN` 在 radiaTest 手动保存 `app_id` 和 `app_secret`。
- radiaTest 新增独立 `bot` 运行进程，使用飞书长连接(Long Connection)接收私聊消息。
- `bot` 进程复用后端镜像和数据库连接，不作为通用消息网关。
- 飞书用户只能绑定已有 radiaTest 用户；除 `help` 或 `帮助` 入口外，使用 Bot 命令前必须先完成绑定。
- 绑定流程从已登录的 radiaTest Web 发起：用户在账号页面点击绑定飞书，扫码确认后写入外部身份绑定。
- 飞书绑定保存 `open_id` 和可用时的 `union_id`；匹配时优先使用 `union_id`，
  没有 `union_id` 时使用 `open_id`。
- 未绑定用户可以发送 `help` 或 `帮助` 获取飞书首页卡片；资源查询和凭据查看仍需要完成绑定。
- 不通过飞书扫码自动创建 radiaTest 用户，不自动分配角色。
- 飞书 Bot 收到消息后，根据飞书身份查找已绑定的 radiaTest 用户，并按该用户当前启用状态和角色鉴权。
- 所有飞书 Bot 命令和卡片交互只允许在私聊中使用；群聊消息不处理。
- Bot 产品范围包含查询型私聊卡片交互、VM 申请和受资源权限约束的远程命令执行。
  其他写命令必须先补充确认、幂等和审计规则。
- VM 申请卡片使用 Bot 进程内表单状态记录用户在单张创建卡上的选择。提交时复用后端
  VM 申请领域逻辑，并持久化原子占用卡片 `form_id`，防止重复回调创建多台 VM。Bot
  重启后，未提交的创建卡需要重新打开。
- VM 申请不新增审计日志；申请单、租约和异步任务事件仍是可追踪记录。
- 远程命令执行(Remote Command Execution)通过飞书资源详情卡片触发，使用资源保存的
  SSH 用户和密码执行单条同步命令。
- 远程命令执行复用资源凭据查看权限，不对 `vm-host` 标签做特殊权限分支。
- 远程命令卡片使用飞书事件 ID 持久化去重，避免重复回调再次执行命令。
- 远程命令执行必须限制命令长度、执行超时和输出长度。命令输出只回传飞书卡片，不保存到数据库。
- 远程命令执行必须写审计日志，记录命令原文和执行摘要，不保存 stdout/stderr。
- Bot 卡片交互的页面层级、列表字段、详情字段和空状态以功能规格(Spec)为准，ADR 不重复记录。
- 不在卡片交互里实现复杂资源筛选系统；复杂资源过滤可通过 LLM 自然语言理解扩展。
- 飞书查看凭据沿用现有凭据权限和审计规则：执行后端鉴权，不记录查看行为，凭据修改仍记录审计。

不采用：

- 不使用飞书作为 Web 登录方式。
- 不在 radiaTest 内创建或发布飞书应用。
- 不支持飞书扫码自助注册。
- 不在群聊中返回资源凭据。
- 不把 Bot 接入设计成多 IM 平台抽象层。
- 不先实现 PAT 再让 Bot 调用 REST API；Bot 作为 radiaTest 内部进程复用后端领域逻辑。
- 不提供交互式远程终端；飞书远程命令执行只执行单条同步命令。

## 影响

- 数据模型需要新增飞书应用配置，用于保存每套环境的飞书 `app_id`、`app_secret` 和启用状态。
- 数据模型需要新增外部身份绑定，例如 `user_identities`，用于保存飞书用户标识和本地用户的关系。
- 部署拓扑增加 `bot` 服务，和 `backend`、`worker` 使用同一后端镜像。
- 用户账号页需要提供飞书绑定入口。
- 资源查询、VM 查询、VM 申请、远程命令执行和凭据查看可以在飞书私聊中复用现有权限规则。
- VM 申请以卡片提交作为显式确认，并使用持久化的单卡片 `form_id` 防重复提交；其他写操作仍需
  另行补充幂等性、确认交互和审计规则。
- 后端镜像需要提供 OpenSSH 客户端和 `sshpass`，用于通过资源保存的 SSH 密码执行命令。
