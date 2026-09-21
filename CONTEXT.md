<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# radiaTest 上下文

radiaTest 是单团队使用的内网 openEuler 测试平台，管理测试资源、资源租约、虚拟机生命周期、测试用例、测试任务、工单和通知。

本文只定义领域语言和核心不变量。页面、API、权限和验收标准以 `docs/spec/` 为准，架构取舍以 `docs/adr/` 为准。

## 资源领域

资源(Resource)：

- 被 radiaTest 纳管的测试机器。
- 分为物理资源(Physical Resource)和虚拟资源(Virtual Resource)。
- 两类资源共享身份、租约、凭据、标签和日志语义，类型专属规格分别保存。

资源编码(Resource Code)：

- 用户和 API 识别资源的稳定业务身份，不是数据库内部主键。
- 物理资源使用设备整机 SN，虚拟资源使用 VM UUID。
- 创建后默认不可修改。

资源显示名(Resource Display Name)：

- 资源的可选可读别名，不参与身份判断。

资源池(Resource Pool)：

- 按实验室、网络区域或用途对资源分类的分组。
- 只用于组织和筛选，不授予权限。

关键资源(Critical Resource)：

- 只有 `ADMIN` 可以占用和查看凭据的资源。

管理状态(Management Status)：

- 资源是否允许进入租约流转，取值为 `active`、`maintenance` 和 `disabled`。

连通状态(Connectivity Status)：

- 按需检查记录的网络可达性，取值为 `unknown`、`reachable` 和 `unreachable`。

占用状态(Occupancy Status)：

- 资源与租约的当前关系，取值为 `idle`、`occupied` 和 `expired`。

租约(Lease)：

- 某个用户在一段时间内占用资源的记录。
- 普通用户使用有限期租约，`ADMIN` 可以创建永久租约。
- 过期租约通过业务读取或操作触发懒释放；VM 租约释放还需要完成 VM 销毁。

凭据(Credential)：

- 登录资源所需的 SSH 或 BMC 账号和密码。
- 物理资源具有 SSH 和 BMC 凭据，虚拟资源只有 SSH 凭据。
- 凭据加密保存，查看和修改遵循不同的鉴权与审计规则。

物理机 PXE 重装(Physical PXE Reinstall)：

- ADMIN 触发的原子装机能力，从 `physical_install_images` 选镜像，PXE 引导重装系统。
- 重装期间资源 `management_status=maintenance`，SSH 验收通过（最长 60 分钟）后恢复 `active` 并更新 SSH 凭据为默认密码 `openEuler12#$`。
- `os_version` 写镜像的 `os_version`，不重复加前缀。

硬件探测回填(Hardware Probe)：

- 重装成功后自动 best-effort SSH 探测硬件（`lscpu`/`dmidecode`/`lsblk`/`uname`）回填 CPU/内存/硬盘/内核/架构/板序列号；探测值非 None 覆盖，`os_version` 不覆盖（重装写镜像版本，之后重装自动刷新）。
- ADMIN 可在详情抽屉点「刷新硬件」手动触发（`POST /resources/{id}/probe`）。
- 不轮询 BMC；重装后 + 手动按钮够用。

VM 宿主(VM Host)：

- 带 `vm-host` 标签、用于创建虚拟机的物理资源。
- 宿主容量以实时检查为准，不由 radiaTest 数据库台账推导。

VM 申请(VM Request)：

- 用户申请创建一台新 VM 的异步工作流记录。
- 申请单保存输入快照、执行状态、错误、宿主尝试和任务事件。
- 创建成功后形成虚拟资源和申请人的租约；VM 不从长期空闲库存复用。

VM 安装方式(VM Install Type)：

- 自动安装使用镜像索引发现的 qcow2。
- 手动安装使用用户提供或上传的 ISO，创建空系统盘并通过 VNC 完成安装。

上传 ISO(Uploaded ISO)：

- 用户为手动安装临时提供的介质。
- 上传后生成宿主可访问的 URL，不形成独立镜像资产。

VM 镜像(VM Image)：

- 从内网镜像仓库目录发现、可用于自动创建 VM 的 qcow2。
- 镜像缓存与每台 VM 的实例盘是不同对象，VM 不直接使用缓存运行。

VM 释放(VM Release)：

- 销毁 VM、释放租约并软删除虚拟资源的异步过程。
- 只有宿主销毁成功后才完成平台侧释放。

VM 电源操作(VM Power Operation)：

- 对已有 VM 执行启动、关机或重启。
- 它是同步短操作，不属于 VM 创建或销毁任务。

## 测试领域

任务事件(Task Event)：

- 异步任务的脱敏执行轨迹，用于诊断阶段和失败原因。
- 任务事件不是审计日志或租约日志，不表达权限追责或资源使用历史。

测试任务(Test Job)：

- 使用指定测试框架和环境配置执行一组测试用例的请求。
- 测试任务固定提交时的 Mugen commit 和用例选择。
- 测试失败(Failed)只表示用例失败或超时；环境、编排或平台问题称为任务异常(Error)。
- 用户主动中止的收敛称为已取消(Cancelled)，不算 Error 也不算 Failed；对应 `case_run.status = not_executed`。

任务取消(Job Cancel)：

- ADMIN 通过流水线 RunJob cancel API 发起的终止请求，`cancel_requested=True` 持久化在 TestJob 与 PipelineRunJob 上。
- Worker 通过 `run_case` 内 15 秒轮询发现标志 → 触发 `cancel_event.set()` → 本地 `run_process` kill sshpass → 并行发 `pkill -f mugen.sh` 释放远程资源。
- 独立 TestJob 尚无 cancel API 端点，只由流水线级联设标志。

测试任务模板(Test Job Template)：

- 可重复使用的测试任务配置，不直接执行任务。
- 模板只负责预填创建表单；创建出的任务保存独立快照，不依赖模板后续状态。

测试环境套(Test Env Set)：

- 测试任务中的一套独立执行环境。
- 一套环境包含一个控制节点和可选的辅助节点，并执行分配给它的 suite bundle。

测试环境节点(Test Env Node)：

- 一台参与测试的虚拟机或物理机。
- 控制节点部署并运行测试框架，辅助节点作为被测或协作节点。

测试用例执行(Test Case Run)：

- 某个 suite/case 在某套测试环境中的一次执行结果。

Mugen 测试框架(Mugen Test Framework)：

- radiaTest 支持的测试框架。
- `suite2cases` 索引提供 suite/case 关系和环境资源约束。
- Mugen 在控制节点部署和执行。

环境准备脚本(Pre Env Script)：

- 每套测试环境执行全部 case 前运行一次的用户脚本。

环境清理脚本(Post Env Script)：

- 每套测试环境执行全部 case 后尝试运行一次的用户脚本。
- 它与环境是否最终销毁是两个不同概念。

用例重跑(Case Rerun)：

- 从重跑链上最新终态 RunJob 选择终态 Case Run，在来源 EnvSet 对应的既有资源中再次执行。
- 候选全集固定为根 RunJob 的用例集合；每个候选的状态与直接来源取该根 Case Run 的链上最新事实，当前批次结果仍独立展示。
- 每次重跑创建新的 RunJob、Test Job、EnvSet、Node 和 Case Run；来源执行事实和日志不可变。
- 跨历史批次混选按根 EnvSet 合并，同一实际环境每批只执行一次局部准备和收尾脚本。

重跑环境准备脚本(Rerun Env Script)：

- 模块模板中用于来源环境局部恢复的脚本，并随 Test Job 保存快照。
- 每个复用 EnvSet 在重跑 case 前执行一次；它不替代首次执行的 Pre Env Script。

## 协作领域

本地用户(Local User)：

- 由 `ADMIN` 创建和维护的 radiaTest 登录身份。
- 用户拥有一个角色：`ADMIN`、`TSE` 或 `TE`。
- 飞书身份绑定不会创建本地用户，也不改变角色。

飞书 Bot(Feishu Bot)：

- radiaTest 在飞书私聊中的交互入口。
- Bot 根据外部身份绑定找到本地用户，再复用 radiaTest 权限规则。
- Bot 不是 Web 登录、用户注册或通用 IM 网关。

外部身份绑定(External Identity Binding)：

- 外部平台身份与已有 radiaTest 本地用户之间的映射。
- 飞书绑定只用于 Bot 识别操作者，不作为 Web SSO。

远程命令执行(Remote Command Execution)：

- 用户通过飞书对自己有权操作的资源执行一次性 SSH 命令。
- 它使用资源凭据，不复用 VM 宿主脚本私钥，也不参与 VM 生命周期编排。

工单(Ticket)：

- 用户提交的需求(`REQ`)或缺陷(`BUG`)记录。
- 工单由 `ADMIN` 接受、拒绝、指派和完成。
- 工单状态单向流转，不支持删除、重新打开或退回。

工单评论(Ticket Comment)：

- 工单参与人追加的交流记录，不改变工单状态。
- 评论提交后不可编辑或删除。

通知(Notification)：

- 面向单个用户的持久化告知记录。
- PostgreSQL 是通知事实来源；飞书只是部分通知的附加投递渠道。
- 通知不是审计日志、租约日志或任务事件。

到期提醒(Expiration Reminder)：

- 有期限资源租约到期前发送给当前租约所有者的通知。

审计日志(Audit Log)：

- 安全或管理操作的追责记录。

租约日志(Lease Log)：

- 资源占用、续期、释放和自动释放形成的使用事件流。

幂等键(Idempotency Key)：

- 客户端为关键写请求提供的重试身份。
- 同一主体、方法、路径、键和请求内容代表同一次业务操作。

## 角色

`ADMIN`：

- 管理用户、全部资源和关键资源，可以查看全部凭据、审计日志和租约日志。

`TSE`（测试系统工程师）：

- 可以维护允许编辑的普通资源、占用普通资源，并按规则管理自己或 `TE` 的租约。

`TE`：

- 可以查看和占用普通资源，并管理自己的租约；不能维护资源或强制释放他人租约。

## 核心不变量

- 资源内部 UUID 与对外资源编码承担不同职责。
- 管理状态、连通状态和占用状态相互独立，不能合并为一个字段。
- 同一资源同时最多有一个有效租约。
- 关键资源只能由 `ADMIN` 占用和查看凭据。
- PostgreSQL 保存业务事实；Redis 只承担 Celery 队列和结果后端。
- 包含宿主机或测试环境副作用的任务不能在 Worker 中断后自动重放。
- 15h 软超时和 DB `cancel_requested` 命中汇入 job 级 `cancel_event`；HangDetector 判挂死只触发当前用例的本地终止信号。`run_process` 的 2 秒分片观察任一信号并保证本地秒级 kill；`SoftTimeLimitExceeded` 到达后不再被 `with ThreadPoolExecutor.__exit__` 的 `shutdown(wait=True)` 阻塞到子命令自然结束（详见 ADR 0031）。
- Pipeline 状态聚合优先级：error > cancelled > failed > succeeded；`cancelling` 与 `preparing/running` 视为非终态。
- 用例重跑只能复用来源节点身份；环境不可用时不得隐式创建替代资源。
- 同一根重跑链的共享资源不能并发执行多个重跑。
- 任务事件、审计日志、租约日志和通知各自表达不同事实，不互相替代。

## 版本管理领域

版本(Version)：

- 一个待发布版本的长期测试对象，如 `openEuler-26.09-DevStation`。
- `name` 与物理机安装源的 `os_version` 同约定（带 `openEuler-` 前缀）。

里程碑(Milestone)：

- 版本下的一个 RC 轮次（`alpha` / `round1`… / `release`），是后续测试活动（软件包比对、用例筛选、测试模块）的载体。
- 与 PXE 装机的 `round` 语义相同，但不参与装配流：里程碑登记的比对构建根 URL（公网 dailybuild）与 PXE 装机源（94 内网 OS 树）互不混用。

软件包比对(Package Compare)：

- 两个轮次间（或轮内双架构间）的软件包差异计算，产出二进制 / 源码 / 同名异构 / 重复包四类视图。
- 比对语义与交付工具保持逐字一致；数据库只存非 `SAME` 变更行，全量交付物按需重算导出。
- 变更包的裸 spec 包名是后续 Mugen 用例匹配的键。