<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# 测试流水线功能规格

## 1. 概述

radiaTest 的测试流水线（Pipeline）在 TestJob 之上引入编排层，支持对 openEuler 多个版本 × 双架构全并行执行测试模块，收集日志和子用例结果，Web UI 看板展示。

流水线是通用能力，支持多种**流水线类型**（`pipeline_type`）；类型由 `pipeline_types` 表注册，分两类：

- **A 类（代码驱动）**：含复杂编排逻辑，每个 A 类对应一个 `PipelineStrategy` 子类，注册在 `PIPELINE_STRATEGIES`。当前 A 类只有 **update 测试流水线**（6 模块：docker、kernel、pkgcmd、pkgmanage、pkgserver、pkgunion）。
- **B 类（数据驱动，"直接跑用例"）**：编排同构——选 framework → 选若干 suite → 每个 suite 顺序跑全部 case。所有 B 类共享 `DirectRunPipelineStrategy`，由 `pipeline_types` 表驱动，前端可增删。当前 seeded B 类有 **release 测试流水线**。

`test_framework`（mugen / 未来其他框架）保持代码注册（`FRAMEWORK_EXECUTORS`），不是前端 CRUD 概念。

关键 ADR：[ADR 0032](../adr/0032-update-test-pipeline.md)（update 高层决策）、[ADR 0033](../adr/0033-update-pipeline-execution-model.md)（执行模型取舍与通用化）、[ADR 0010](../adr/0010-pipeline-type-registration-data-vs-code.md)（类型注册数据驱动 vs 代码驱动）。

## 2. 领域语言

- **Pipeline（测试流水线）**：TestJob 之上的通用编排层。一条流水线由配置定义，可多次触发。
- **Pipeline Type（流水线类型）**：`pipeline_types` 表的注册概念，`pipeline_configs.pipeline_type` 逻辑引用 `pipeline_types.name`（不加物理 FK）。分 A 类（代码驱动，如 update）和 B 类（数据驱动，如 release）。前端可增删 B 类；A 类由 seed 管理。
- **Pipeline Config（流水线配置）**：稳定的流水线定义，包含名称、`pipeline_type`、版本列表、架构列表、`dist`、`image_round`、`test_framework`、类型专属 `config_data`。可多次触发；触发时 trigger 级 `image_round` 可覆盖 config 级。
- **Pipeline Execution（流水线执行）**：一次触发产生的一条执行记录，包含本次触发的版本列表和架构列表。包含多个 Run（每个版本一条）。
- **Pipeline Run（版本子流水线）**：一个版本的一次执行。包含多个 RunJob。
- **Pipeline RunJob**：一个模块在一个架构上的执行单元，一个 RunJob 对应一个 TestJob。模块模板的 `env_type` 决定环境形状：`both` 建一个 RunJob（`env_type=null`）和最多两个 VM/物理机 EnvSet；`physical` 建一个 physical RunJob；`vm` 建一个 VM RunJob。
- **Test Module Template（测试模块模板）**：可复用的模块定义，包含 Mugen suite、环境配置、pre_env_script、rerun_env_script、post_env_script、result_parser、mugen_exec_command 等。A 类流水线（update）由用户在 UI 显式管理；B 类（release）在触发时按 `config_data.case_selections` 调 `_find_or_create_release_template` 自动建单个带默认 `post_env_script`（日志拷贝）的模板（每架构一套环境跑全部 suite，共一个模板）。
- **PipelineRunNodeInfo（执行机信息）**：RunJob 关联的 VM/物理机信息，用于看板展示和跳转。
- **TestCaseRunDetail（子用例结果）**：Mugen 用例内部的子测试结果。
- **keep_env（全保留环境）**：TestJob 标志，为 True 时所有环境不管成败保留到人工销毁，用于流水线。与 `keep_failed_env`（只保留失败环境）区分。
- **Image Round（镜像轮次）**：镜像仓库 URL 第三段，标识某一轮构建的 qcow2 镜像。VM 自动安装模式下必填。流水线双层归属：`PipelineConfig.image_round` 为配置级值（适用 update 等基础镜像稳定的场景），`PipelineTriggerRequest.image_round` 为触发级覆盖（适用 release 等每次 RC 换轮的场景）。
- **Distribution / dist（发行版）**：镜像仓库 URL 第一段，标识发行版，如 `openEuler`。流水线配置期间稳定，存在 `PipelineConfig.dist` 顶层字段，默认 `openEuler`。

## 3. 数据模型

### 3.1 新增表

| 表 | 说明 |
| --- | --- |
| `pipeline_types` | 流水线类型注册：name（唯一）/display_name/strategy_kind（`update_strategy` \| `direct_run`，dispatch key）/test_framework/is_system（seeded 系统类型不可删）/default_config（类型级默认 JSON） |
| `test_module_templates` | 模块模板：name, suite_name, env_set_num, node_num, case_filter, env_type(vm/physical/both), pre_env_script, rerun_env_script, post_env_script, result_parser, test_framework, mugen_exec_command |
| `pipeline_configs` | 流水线配置：name, **pipeline_type**（逻辑引用 `pipeline_types.name`，不加物理 FK）, versions, archs, dist, image_round, test_framework, config_data（类型专属 JSON，如 update 的 `module_template_ids` / release 的 `case_selections`+`kernel_variant`+`kernel_rpm_url`） |
| `pipeline_executions` | 流水线执行：config_id, triggered_by, triggered_at, completed_at, status, versions, archs |
| `pipeline_runs` | 版本子流水线：execution_id, config_id, version, status, triggered_by |
| `pipeline_run_jobs` | 模块×架构执行单元：pipeline_run_id, module_template_id, arch, env_type（`both` 时为 null）、test_job_id, task_id, status；环境差异由关联 TestJob 的 EnvSet 表达 |
| `pipeline_run_node_infos` | 执行机信息：run_job_id, resource_id, resource_code, primary_ip, role, env_set_index, node_index, status |
| `test_case_run_details` | 子用例结果：case_run_id, sub_test_name, status, detail |
| `test_log_artifacts` | 日志文件记录：pipeline_run_id, job_id, module, arch, artifact_type, artifact_name, storage_path |

Seed 两条 `pipeline_types`：`update`（`strategy_kind=update_strategy`, `is_system=True`）和 `release`（`strategy_kind=direct_run`, `is_system=True`）。

### 3.2 扩展现有表

| 表 | 扩展字段 |
| --- | --- |
| `test_jobs` | `physical_usage_scenario` (nullable, 物理机用途快照)；`mugen_exec_command` (nullable, 自定义 Mugen 执行命令)；`keep_env` (bool, 默认 False, 全保留环境标志)；`result_parser` (nullable, 子用例解析器, builder 从模板复制)；`pipeline_extras` (JSONB nullable, 类型专属执行参数；release 存 `kernel_variant`/`kernel_rpm_url`，后续新流水线的专属字段均入此 JSON，不再逐类型加列) |
| `test_case_run_status` 枚举 | 新增 `NO_CASE`（未找到用例，pkgcmd 无 mugen 用例的包）+ `NOT_EXECUTED`（未执行，物理机禁用/64k 跳过）；`SKIPPED` 改为只管 mugen 自己 skip（mugen 跑了但用例内部跳） |

## 4. 通用执行模型

### 4.1 编排形态

trigger（HTTP）只建 Execution + Run + RunJob 空壳（`status=pending`），投递前为每个
RunJob 持久化 Celery `task_id`，再发送 `run_pipeline_run_job` 任务并立即返回 Execution。
全并行：所有 RunJob 任务同时进队列，靠 worker 并发吃。`run_pipeline_run_job` 必须
fail-safe——所有异常自己 catch、标 RunJob=error、绝不 raise，保证 finally 自汇集可靠执行。

### 4.2 run_pipeline_run_job 任务

每个 `run_pipeline_run_job(run_job_id)`：
1. Worker 领取任务后写带相同 Celery task ID 的 started 事件，RunJob → `preparing`，
   读取并校验所属 Run、配置和模块模板。
2. RunJob → `running`。按 `case_filter`（见流水线类型的 case 策略）+ 模板字段建
   TestJob：继承 RunJob `task_id`，设置 `physical_usage_scenario`、`keep_env=True`、
   `env_type`、`arch`、`os_version`、从模板复制的 pre/post_env_script/mugen_exec_command；
   建 EnvSet/Node/CaseRun，并将 TestJob ID 写入 `run_job.test_job_id`。**绕开
   `create_test_job`**（其 VM-only 策略门和手动选 case API 不适配流水线）。建完
   TestJob 后 **`db.commit()`**——`process_test_job` 开新 session，未 commit 的行在
   PostgreSQL 中对新事务不可见。
3. 调 `process_test_job`（**复用执行机器**）；Pipeline 内创建的 VMRequest 继承同一
   `task_id`。
4. 完成后 RunJob → `{succeeded|failed|error|cancelled}`（worst-wins from
   TestCaseRun / TestJob 终态：error > cancelled > failed > succeeded；
   TestJob=cancelled → RunJob=cancelled，TestJob=error → RunJob=error，…）。
   Worker 收到用户取消请求后 RunJob 先进入 `cancelling`（非终态），最终由
   `_map_job_status(TestJob.status)` 收敛为 `cancelled`。
5. finally 块：从 `run_job.test_job_id` 获取 TestJob，自汇集日志（见 4.8）。

### 4.2.1 Mugen 部署前置

`prepare_mugen` 在 `git clone mugen` 之前先 `dnf install -y git python3 python3-pip`——official openEuler qcow2 镜像默认不装 git/python3-pip。用 `|| true` 容错（已装的包不影响）。

### 4.2.2 SSH 连接

`run_ssh_command`（worker → VM 的 SSH 调用）固定带 `-o GSSAPIAuthentication=no -o PreferredAuthentications=password`——official 镜像 sshd 支持 GSSAPI 但内网无 DNS/KDC，GSSAPI 查询会无限挂起。跳过 GSSAPI 直接走密码认证，2 秒内连上。

`wait_for_ssh_ready` 超时 900 秒（15 分钟），每 10 秒重试一次，每 3 次重试（~30 秒）记录一条 `ssh_retry` task event（含具体 SSH 错误 stderr/stdout）。

`build_env_file` 注入 `OET_PATH=/opt/mugen` 到 `kronos.env`，`pre_env.sh`/`post_env.sh` 通过 `source kronos.env` 获取。模块脚本中引用 mugen 路径时使用 `${OET_PATH}`（如 `${OET_PATH}/logs/`、`${OET_PATH}/results/`），不硬编码 `/tmp/mugen` 或 `/opt/mugen`。前端模板编辑输入框展示 `OET_PATH` 提示，方便新模块编写。

### 4.2.3 终止收敛机制

RunJob/TestJob 的取消与软超时使用 job 级 `threading.Event`；挂死只使用当前
用例的本地 `threading.Event`。两类事件都能打断正在执行的子进程，分三层：

- **信号层**：`process_test_job` 顶层持有 job 级 `cancel_event`，一路传给
  `_run_env_set_thread` → `execute_env_set` → `prepare_env / configure /
  run_hook / wait_for_ssh_ready / run_case`。主线程
  `except SoftTimeLimitExceeded`（15h 软超时）和从 `preparing` 起每 15 秒检查一次
  DB `cancel_requested=True` 的 watcher 都可以 set job 级事件；因此 VM 创建完成后、
  环境准备或用例执行中的取消都会中断下一步可取消操作。`run_case` 为每个
  用例另建本地事件，`HangDetector.on_hung` 挂死判定（心跳连续 max_failures 次
  失败且复核一次仍失败；有 BMC 的物理机另经带外确认或观察模式后判定，见 4.6）
  只 set 该事件。
- **执行层**：`run_process` 支持一个主 `cancel_event` 和附加取消事件；selectors 分片最多
  2 秒；命中即 `process.kill()` 本地 sshpass 子进程并返回
  `ProcessResult(cancelled=True)`，与 `timed_out=True`（步骤自然超时）语义
  分离。所有 `run_control_command` 上层（`wait_for_ssh_ready` /
  `configure_mugen_node` / `run_hook` / `prepare_mugen` / `prepare_env` /
  `write_control_file` / `archive_rerun_case_outputs`）见到
  `result.cancelled` 或 job 级 `cancel_event.is_set()` 立刻
  `raise TestJobExecutionError("job_cancelled", ...)`；挂死事件则由 `run_case`
  进入原有 `EnvSetHangError` 分支。`_cancel_watcher`
  命中 DB cancel 后按顺序：set `cancel_event`（本地 kill）→ 新开 SSH
  `pkill -f mugen.sh`（远程资源释放）。
- **收敛层**：`_run_env_set_thread` 捕获 `job_cancelled` 时把本 env_set 的
  剩余 PENDING case 收敛为 `NOT_EXECUTED` + `cleanup_env_vms(preserve=False)`，
  然后返回不带 error 的 `_EnvSetResult`；主线程按来源决定终态：
  - DB `cancel_requested=True` → `TestJobStatus.CANCELLED` → RunJob
    `_map_job_status("cancelled")` → Pipeline 聚合显示 cancelled；
  - `SoftTimeLimitExceeded` → `handle_job_execution_error(code="task_timeout")`
    → `TestJobStatus.ERROR` → RunJob `error`；
  - 挂死 case 走原 `EnvSetHangError` 分支不进入 `job_cancelled` 打断链；其本地
  事件在用例结束后废弃，不影响同环境集后续用例或兄弟环境集；若取消在 TestJob
  启动前或 Mugen TestJob 构建后命中，尚未执行的 EnvSet 和 CaseRun 直接收敛为
  `not_executed`，不创建环境。

**响应时间**：
- Soft / 挂死 → 本地 kill 由 `run_process` 2s 分片保证 ≤5s。
- DB 主动取消 → 端到端受 `_cancel_watcher` 15s 轮询周期约束，本地 kill 仍需
  ≤5s，总计约 ≤18s。

**支持**：worker 存活期间的取消、软超时与挂死都能秒级或半分钟级收敛；
`handle_job_execution_error` 保留 `keep_failed_env` / `keep_env` 语义，
`cleanup_failed_job_envs` 只在真异常路径调用。

**不支持**（下一轮的范围）：
- 非流水线 TestJob 的独立 cancel API（`cancel_requested` 字段与执行期检测
  已就绪，只缺 `POST /test-jobs/{id}/cancel` 端点写入）。
- `mugen_exec_command = "docker exec ... mugen.sh"` 场景下的容器 PID
  namespace 感知的远程 pkill（本地 kill 已由本次 cancel_event 通路覆盖，
  容器内 mugen.sh 进程需下一轮）。

### 4.3 状态聚合

RunJob 状态由任务设（`pending → preparing → running → {succeeded|failed|error|cancelled}`；
ADMIN 用户从 `running|preparing|pending` 可发起取消 → `cancelling`（非终态）→ 最终 `cancelled`
或因内部错误收敛为 `error`）。
`preparing` 表示 worker 已领取并校验所属 Run、配置和模板；`running` 包含 TestJob
构建、仓库元数据读取、环境准备和测试执行。仓库元数据拉取失败 → `error`，不与
"执行失败"混。`error` = 环境/挂死/元数据/意外（对齐 CONTEXT.md 的 Error vs Failed）。
`cancelled` = 用户主动终止或兄弟 env_set 被终止后 job 的收敛语义，不算执行失败，
不算 error。

Run/Execution 状态**不存、不更新、不要 counter**：API 读看板时实时从 RunJob
worst-wins 推算（任一子非终态 → 父 `running`；`cancelling` 也视为非终态；
否则 error > cancelled > failed > succeeded。人为截断意味着剩余用例没测完，
运维优先关心"为什么被取消"，所以 cancelled 排在 failed 之上）。Worker 启动时，具有 `task_id` 和 started 事件且仍为 `preparing/running`
的旧 RunJob 自动收敛为 `error`；`cancelling + cancel_requested` 的旧 RunJob 及其关联
TestJob 收敛为 `cancelled`。RunJob 详情、Run 下 Job 列表和 Execution 汇总读取时，started
事件超过 15 小时的 RunJob 使用 `task_timeout` 懒恢复。普通关联 TestJob 收敛为 `error`，
关联的 `creating/queued` VMRequest 收敛为 `failed`；恢复不修改 EnvSet、Node、CaseRun，
也不连接宿主机或清理环境。

`compute_run_status(db, run)` 和 `compute_execution_status(db, execution)` 在 Router 层覆盖 stored `status` 字段——`PipelineExecution.status` 和 `PipelineRun.status` 虽然是 DB 列（默认 `pending`），但所有 GET 端点返回 computed 值而非 stored 值。

### 4.4 物理机执行模式

流水线按 EnvSet 的环境类型创建物理机或 VM。kernel 使用 physical RunJob；pkgcmd/pkgserver 的 `both` RunJob 在同一个 TestJob 内分别执行 VM 与物理 EnvSet。物理 EnvSet 使用触发者已占用、**用途标记 `usage_scenario`=`<模块名>-update`** 且架构匹配的物理机（kernel→`kernel-update`、pkgcmd→`pkgcmd-update`、pkgserver→`pkgserver-update`），避免误装其它重要机器。流水线触发前按唯一 `(arch, usage_scenario)` 检查每组至少一台当前用户已占用、管理状态 active 且未被非终态 Test Job 使用的机器；任一组不可用时整次触发返回 `409`，不创建部分执行。多个版本共享同组机器排队，不要求机器数等于版本数。

worker 用数据库行锁认领候选资源并立即写入物理 Env Node 的 `resource_id`；后续 worker 根据非终态 Test Job 的节点关联等待机器释放，最长不超过当前 Test Job 的 15 小时总截止时间。被认领后按 pipeline `version`+`arch` 找 `physical_install_image`，RunJob 内同步调 PXE 重装（抽出的 `run_pxe_install(...)`，等 SSH 通，复用 `verify_host_key=False`）后再跑 mugen。`-64k` 版本当前只支持 `openEuler-24.03-LTS-SP4-64k`/aarch64，使用去掉后缀的基础 PXE 镜像，但把保留 `-64k` 的 Test Job 目标版本传入 PXE 后处理；基础系统安装完成后只检查最新 update 轮，安装 `kernel-64k`、设置默认 GRUB 启动项、重启并等待 SSH 恢复，且 `getconf PAGESIZE=65536` 后才把物理 Env Node 标为 `ready`。最新轮无 64k 时，当前 Node、EnvSet、Case 收敛为 `not_executed`，Test Job 正常成功，物理机保留基础 SP4 并恢复 active；安装或启动验证失败时 Node `error`、物理机 disabled（[ADR 0015](../adr/0015-kernel-module-envtype-physical-reinstall-result-dispatch.md)、[ADR 0024](../adr/0024-vm-64k-kernel-post-processing.md)、[ADR 0029](../adr/0029-physical-test-resource-usage-state.md)）。Resource API 在节点所属 Test Job 非终态期间派生 `test_status=testing`；环境准备完成后 `management_status` 恢复 active，不代表测试空闲。

### 4.4.1 EnvSet 并行执行

同一 TestJob 的 EnvSet 可并行完成环境创建、Mugen 部署、前置脚本、用例和后置脚本；EnvSet 之间互不依赖，并发上限为 4，避免 VM 宿主过载。

`env_type=both` 的并行发生在同一 TestJob 的 VM 与物理 EnvSet；两者由同一个 RunJob 的 `ThreadPoolExecutor` 并行执行。EnvSet 并行也用于同一环境类型的多个 EnvSet（如 pkgmanage 的 01/02）。

挂死检测不受影响：HangDetector 在 `run_case` 内按 env_set 独立运行，一个 env_set 挂死不影响其他 env_set（不同 VM）。`finally` 块的 post_env_script 也各 env_set 独立执行。所有 env_set 完成后，主线程聚合 worst-wins 设 TestJob 状态。

### 4.5 VM 全保留

pipeline TestJob 的 `keep_env=True`，`process_test_job` 在 `keep_env=True` 时跳过 cleanup，所有 VM/物理机环境保留到发版后人工统一销毁（见 6.3 `destroy-envs`）或 5 天租约自动过期。`create_env_node_vm`/`create_env_node_physical` 在 `keep_env=True` 时设 `expected_ends_at = created_at + 5 天`（不同于普通任务的 15 小时总超时）。`create_env_node_vm` 不 strip `-64k` 后缀——`-64k` 信号传给 `process_vm_request`，流水线只检查最新 update 轮并在 VM 创建阶段完成 64k 启动验证（[ADR 0024](../adr/0024-vm-64k-kernel-post-processing.md)）。最新轮未转测时，环境创建结构化返回当前 EnvSet 的 `NOT_EXECUTED`，不查询全局 TaskEvent 文本。普通 VM 申请仍可回退最多 5 个轮次。`keep_failed_env` 语义不动（只保留失败 env，非流水线 TestJob 行为不变）。非 `keep_env` 场景下，cleanup 在所有 env_set 并行完成后再逐个执行。`HOOK_TIMEOUT_SECONDS` = 3600（docker pre_env 10 步累计需 30-40 分钟，1800 不够）。

### 4.6 挂死检测和处理

`run_case` 启动后台心跳 HangDetector（30s 间隔 SSH `echo ok`，30s 超时，5 次连续失败达阈值）+ 执行前在被测节点写 `/tmp/kronos-current-case` = `suite/case`。达阈值后先复核一次（等待一个 interval 复查，仍失败才进入判定分支；复核成功则失败计数清零、用例继续执行），避免把压线的 SSH 瞬断判死（[ADR 0042](../adr/0042-physical-hang-confirmation-and-bmc-forensics.md)）。**带外确认与观察模式（[ADR 0044](../adr/0044-physical-hang-bmc-cross-check-watch-mode.md)/[ADR 0046](../adr/0046-vm-outofband-hang-recovery.md)）**：复核仍失败后按环境类型做带外三态确认——配置了 BMC 的物理机经 `ipmitool chassis power status`（on/off/查询失败），有宿主通道的 VM（`virtual_spec.host_resource_id` 指向宿主且 `vm_host_ssh_key_path` 已配置）经宿主机 `virsh domstate`（活态 running/paused 等 → 机器在/死态 shut off/crashed/dying → 机器关/查询失败 → 不下结论）。任何三态都进入**观察模式**暂缓判死：心跳保持 30s 不变，带外复查降频为每 3 分钟一轮。SSH 心跳恢复 → 记 `hang_recovered`（info）事件、用例继续执行（sssd-nss 类 NSS 阻塞 3–5 分钟自愈场景拿回用例真实结果）。带外报告死态（电源 off / domstate 关机，含阈值首查）→ 从首次死态起锚定 10 分钟宽限（覆盖正常重启与 on_crash 自动拉起），宽限内 SSH 恢复则继续执行，到点未恢复 → 判挂死，宽限取代观察上限；全程活态或查询失败 → 观察满 30 分钟（代码常量）兜底判死。物理机判死只信电源状态：SEL 时间戳依赖 BMC 时钟（现场观测漂移可达小时级）且事件内容可虚构，不参与判定，仅随取证产物原样采集。进入观察与出结论（恢复或判死）时各抓一次取证（物理机 artifact 名 `bmc-<suite>-<case>-watch-entry.log` / `-watch-recovered.log`，VM 为 `console-<suite>-<case>-watch-entry.log`），观察中首次读到死态追加一条 `hang_watch` 事件。无 BMC 物理机、凭据不可用与无宿主通道的 VM 不做交叉确认，维持阈值+复核即判；观察期间取消/软超时语义不变。心跳失败按传输特征分类计数（失联/超时/拒绝/断连/其他），判挂死时摘要并入错误详情，死态宽限判死或观察超时场景在详情中注明关机证据来源（"BMC 报告电源断开"/"宿主机报告 VM … 已关机"）与"N 分钟内 SSH 未恢复"/"观察期 N 秒未见恢复"。挂死时按环境类型取证：VM 经宿主机 `virsh domstate/console` 存 `console_diagnostic` artifact（宿主信息从 `virtual_spec` 解析）；物理机经 BMC 执行 `ipmitool sel list`/`chassis status`/`sdr elist` 存 `bmc_diagnostic` artifact（best-effort，凭据来自 `physical_spec` 的应用层加密密文，密码经 stdin 传入 ipmitool 不入进程参数）。当前 case 标 `ERROR`（`error_code=vm_hang`）→ `EnvSetHangError` 抛回 `execute_env_set`。

`execute_env_set` 捕获 `EnvSetHangError` 后**不再**标全部剩余 case + break，改为：当前 case 已被 `run_case` 标 ERROR，`execute_env_set` 只做计数 +1 并 `continue` 到下一个用例——给 HangDetector 自愈机制（VM 短暂抖动后恢复）和 SSH `ConnectTimeout` 一个自然处理的机会。同理 catch `RemoteCommandError`（SSH 连不上）：标 ERROR + 计数 +1 + `continue`。用例正常完成时重置计数。**用例间探针（ADR 0046 修订，job 10235）**：每个用例执行前与 post_env 前对控制机做一次 SSH 探活，**只认 `Connection refused`**（sshd 挂了但 OS/网络活着的确定签名，如 crypto-policies 用例触发 systemd start-limit）且有宿主通道时，先做硬复位恢复再继续——victim 用例拿回真实结果，末尾用例杀掉 sshd 的 job 不再因 post_env 失败误标 error；超时/失联不触发（机器状态未知，交给挂死链路）。恢复预算按尝试计且与熔断点共享：探针尝试过恢复（无论成败）即耗尽该环境集预算。**关键边界强制刷盘（ADR 0046 修订二，job 10237/10238）**：硬复位等价拔电，复位前未落盘的页缓存写回会丢失——环境就绪后与每个用例正常返回后对 control 执行 best-effort `sync`（门控在宿主通道存在），把丢失面收敛到杀手用例自身（其日志由 console 取证覆盖）；sync 失败静默（SSH 已死是杀手用例的预期场景），下轮探针恢复接管。**熔断与宿主机恢复（[ADR 0046](../adr/0046-vm-outofband-hang-recovery.md)）**：连续 3 个 vm_hang/RemoteCommandError 后（VM 真死场景，每个浪费 ~10s SSH 超时），有宿主通道的 VM 且预算未用时先尝试恢复：记 `vm_recovery_started`（文案区分探针/熔断触发来源）→ 抓 console 存 `console-recovery.log` → 宿主机 `virsh destroy`+`virsh start` 硬复位（等价拔电重启，磁盘结构保留但复位前未刷盘的近期写会丢，由上文的边界刷盘机制收敛）→ 轮询 SSH 就绪最长 15 分钟（`SSH_READY_TIMEOUT_SECONDS`，受任务剩余时间与取消约束）；SSH 恢复 → 记 `vm_recovered`，连击计数清零、继续执行剩余用例（肇事用例保持 error）；复位失败或 SSH 未回 → 记 `vm_recovery_failed`，剩余 case 批量标 ERROR + break。无宿主通道（物理机、静态无宿主引用、key 未配置）直接批量标 ERROR + break，与原熔断行为一致。`run_hook`（pre_env/post_env）的 `RemoteCommandError` 不在 case 循环 catch 范围内，仍向上传播终止 TestJob（post_env 前探针恢复失败时同样维持该行为）。其他 env_set 在各自线程继续（不同 VM，不受影响）。TestJob 最终 `ERROR`（非 `FAILED`）。平台不据挂死判定自动重启物理机，BMC 取证只用于人工定界，物理机生命周期归调用方；宿主机硬复位仅针对任务期租约独占的 VM。

### 4.7 子用例解析

`run_case` 正常结束（returncode 0 或非 0 都解析；超时/挂死不解析）后，按 `job.result_parser` 选解析器，SSH 拉文件到 worker 解析，结果写入 `test_case_run_details`。子用例的唯一作用是让统计卡片显示通过/失败计数，实际细节由报告或 mugen results 目录展示。解析器按模块分派，可扩展：`parse_ltp_log`（kernel，数 LTP TPASS/TFAIL 子用例）、`parse_mugen_results_dir`（docker/pkgcmd/pkgserver，数 mugen results succeed/failed/skipped）、`parse_pkgmanage_log`（pkgmanage，只数 `fail_list` 段失败包总数，每个失败包一条 `status=failed` 子用例，不带操作类型前缀；无 `fail_list` 段时不产生子用例）。

### 4.8 日志 per-RunJob 自汇集

每个 `run_pipeline_run_job` 任务在 finally 块（无论 success/fail/error/hang 都跑）从 `run_job.test_job_id` 获取 TestJob（executor 只返回 status 字符串，不返回 job 对象），SSH 到本 RunJob 的控制节点拉 `/opt/{template.name}-logs/*` → 逐文件 `store_artifact`（写共享卷 + 建 TestLogArtifact 记录）。每个 RunJob 各自拉各自的，互不依赖——1-2 个挂死/丢失任务不影响其他 RunJob 日志落盘。挂死 RunJob 的 `/opt/{template.name}-logs/` 拉取大概率失败（SSH 也死），best-effort 跳过；挂死取证 artifact（VM `console_diagnostic` / 物理机 `bmc_diagnostic`）已由挂死处理抓取。worker 容器挂载 `/data/test-logs` 共享卷，`LogCollector(base_dir=/data/test-logs)`。

日志自汇集同时处理文件和目录：普通文件走 `scp`（`scp_file` 下载全文到 worker 磁盘，不经 stdout、不截断）+ `store_file_artifact`（`artifact_type="module_log"`，`storage_path` 指向本地文件）；目录走 `scp -r` + `store_dir_artifact`（`artifact_type="pkg_folder"`，`storage_path` 指向本地目录）。目录 artifact 的文件列表和单文件内容通过独立 API 读取（见 5.5）。

**逐 case 原子上传（[ADR 0048](../adr/0048-per-case-log-atomic-upload.md)）**：每个用例正常收敛（passed/failed/timeout/skipped）后，runner 内联同步把该 case 的 mugen 执行日志目录（`/opt/mugen/logs/{suite}/{case}/`）与 results 桶目录（`/opt/mugen/results/{suite}/{succeed|failed|skipped}/{case}`）上传到服务端共享目录 artifact 的对应子路径（docker 模块先 `docker cp` 到宿主机再传）。落位原子：先 scp 到临时目录再 rename，单 case 要么完整可见要么不存在。挂死、SSH 传输失败、取消、15h 超时路径不上传（由 console/BMC 取证 artifact 覆盖）。逐 case 上传 best-effort 单次不重试；结束补拉（上述 finally 自汇集）改为补漏式——目录 artifact 已存在仍重拉全量，填补逐 case 上传失败的缺口（mugen 日志文件名含时间戳，同名幂等覆盖）。case 级 mugen 日志查看（`get_case_mugen_log`）按 `job_id + pkg_folder + 名字以 logs 结尾` 查询，逐 case 落位与结束补拉写同一目录，查看路径不变。

"汇总"= Execution 总看板 API（`GET /pipelines/executions/{id}/summary`）read-time 聚合所有 RunJob 状态/计数/日志/节点 IP，无汇总 task。

## 5. Web UI 看板

### 5.1 设计

导航/页面标题为"**流水线**"（通用）。流水线类型由 `pipeline_types` 表注册，前端配置创建表单的 `pipeline_type` 下拉从 `GET /pipelines/types` 获取。看板支持 Execution 总矩阵 → Run → RunJob → Mugen 用例 → 日志的多级下钻；`execution-detail.vue` 和 `run-job-detail.vue` 不拆分，按 `strategy_kind` 条件渲染：update 显示模块脚本/exec_command 区域，direct_run 隐藏；矩阵列名 update 用 `display_name`，direct_run 用 suite 名。

路由 title 区分：`/pipelines/executions/:id` → "执行详情"，`/pipelines/runs/:id` → "Run 详情"，`/pipelines/run-jobs/:id` → "RunJob 详情"，`/pipelines/runs/:runId/logs/:artifactId` → "日志查看"，`/pipelines/configs/:id/executions` → "流水线配置详情"。各页面 `onMounted` 动态设 `document.title`（如 `RunJob: Docker/aarch64`）。

`execution-detail.vue` 每 10 秒自动刷新 `loadExecution()`，无需手动点刷新。

### 5.2 Execution 总矩阵

路由 `/pipelines/executions/:id`。行=版本，列=模块分组×架构子列（双层表头，6 模块 × 2 架构 = 12 列）。每个模块/架构格对应一个 RunJob；`env_type=both` 的格子展示该 RunJob 的聚合状态和计数，节点信息在同一 RunJob 详情中按 EnvSet 展示。`-64k` 版本仅生成 aarch64 列（x86_64 组合自动跳过，前端版本选择器提示"64k 版本仅支持 aarch64"）。

格子内容：状态色块（succeeded 绿 / failed 红 / error 橙 / 超时 灰底斜纹 / pending 浅 / preparing 青 / running 蓝；`pending→待执行`）+ 下方计数：`通过`/`失败` 常显，`执行中`(running)/`待执行`(pending)/`未执行`(not_executed)/`跳过`(skipped)/`未找到用例`(no_case)/`异常`/`超时` >0 才显。点状态块 → RunJob 详情页。点版本行名 → Run 页。read-time 从 summary API 聚合。

### 5.3 Run 详情

路由 `/pipelines/runs/:id`。单版本模块×架构矩阵，格=状态 + **执行机 IP Tag**（PipelineRunNodeInfo，点 IP 跳 VM 管理页）。作为"单版本+IP 聚焦"中间层。

### 5.4 RunJob 详情

路由 `/pipelines/run-jobs/:id`。上下结构：
- 顶栏：RunJob 元数据（模块/架构/环境/状态/错误码/错误信息）+ 节点 IP 小标签（compact，点跳 VM 页）+ 执行过程时间线（默认折叠到最新 3 条，"展开全部"按钮展开完整时间线）。
- 统计卡片：分两行（[ADR 0037](../adr/0037-runjob-stats-and-suite-header-display.md)）。**用例行**：`总计`/`通过`/`失败`（常显），`跳过`(skipped)/`待执行`(pending)/`未执行`(not_executed)/`执行中`(running)/`异常`/`超时`（>0 才显），按 mugen 用例（TestCaseRun）计数；`总计`不含 `no_case`（未找到用例的包，包维度归包行），等于各状态计数之和。**包行**（仅 `result_parser=pkgcmd`）：`找到用例`(有 mugen 用例的包数) / `未找到用例`(no_case 包数)——pkgcmd 专用维度（`plan_cases` 按 `suite_name==包名` 匹配，no_case 包即没找到用例的包）；其余模块无此行。
- 左栏（3fr）：Mugen 用例列表按 suite（pkgcmd 下 suite=包名）分组。分组头：suite 全 `no_case`→`未找到用例`；全 `not_executed`→`未执行`；全 `skipped`→`跳过`；全 `pending`→`待执行`；有 `running`/`pending`（执行中、非全 pending）→ `执行中 a/x`（a=已出结果数，含通过/失败/超时/异常/跳过，x=总数，蓝底）；其余（全终态）→ `通过 a/x`（a=通过数、x=总数，a=x 绿底、a<x 红底）；筛选某状态时显 `<状态> b`（b=该状态条数，无 /total）。case 行：status Tag + case_name + exit_code，标签 `pending→待执行`、`not_executed→未执行`、`skipped→跳过`、`通过`/`失败`/`未找到用例`/`执行中`/`异常`/`超时`；语义：`跳过`=mugen 跑了但用例内部跳，`未执行`=物理机开关关/64k 未转测不会跑，`待执行`=pending 会跑排队中。状态筛选（全/通过/失败/跳过/未找到用例/未执行/异常），搜索。case 行可点击，跳转到该 case 的 mugen 日志页（§5.5b）。
- 顶部“用例重跑”按钮打开双栏选择器。来源必须是重跑链上最新的终态 RunJob，默认勾选全部
  最新状态为 `failed` 的根 Case Run，也可选择最新状态为 `passed`、`error` 或 `timeout` 的候选。
  候选全集始终来自根 RunJob，不因中间批次只重跑部分用例而缩小；状态、直接来源和摘要取每个根
  Case Run 在链上的最新事实。`skipped`、`no_case`、`not_executed` 展示但不可勾选。同名用例按根
  EnvSet 独立展示，支持 Suite/Case 搜索、状态筛选、环境套标签、最新结果批次标签、“恢复默认失败项”
  和“清空”；筛选栏“全选”仅作用于当前 Suite 视图内匹配当前筛选条件（状态、环境套、关键词）的可见
  用例，且只勾选其中可重跑的项，三态显示全选/半选，取消勾选只取消当前可见可选项；自动刷新不改变
  选择草稿。提交后进入新 RunJob 详情。
- 新 RunJob 使用来源 Test Job 快照创建新的 Test Job、EnvSet、Node 和 Case Run。Case Run 保存直接
  来源和根来源；直接来源指向该根用例的最新 Case Run。EnvSet 按根 EnvSet 分组，Node 复用根来源
  resource。VM 不重新申请，物理机
  不执行 PXE；两者都跳过 Mugen 部署和完整 `pre_env_script`。
- 每个复用 EnvSet 在 case 前执行一次来源快照中的 `rerun_env_script`，再执行所选 case，并在 finally
  中尽力执行 `post_env_script`。重跑脚本失败时，该 EnvSet 未执行的 Case Run 标记 `error`，任务以
  `rerun_env_failed` 收敛，不覆盖来源结果。
- Docker 模块的重跑脚本重启既有 `openEuler_test` 容器并等待其恢复运行；不重启 Docker daemon，也不重新
  安装 Docker、拉取镜像或重建容器。其他已有模块和自动创建模板默认使用空脚本。
- 详情顶部使用紧凑执行历史栏展示首次执行和历次重跑的状态、时间与用例数量。每批结果和日志独立
  展示；总览按根 Case Run 取链上最新结果，未选择的 case 沿用此前结果。
- 右栏（1fr）：**执行结果块——按 `result_parser` 派发**（每模块封装自己的结果展示，互不影响）。pkgcmd 模块（`result_parser=pkgcmd`）隐藏右栏，左栏全宽展示，执行结果由 case 点击跳转 mugen 日志替代。其他模块右栏不变：默认每个 case 展示 status Tag + name + exit_code + `stdout_summary`（pre 块）+ `stderr_summary`（pre 块）。pkgmanage 模块特殊：执行结果区不展示 stdout/stderr，改为内联展示 `pkgmanage-details.log` 报告全文（按 env_set 分块，每块标注 case 归属），报告内容含 `test -n` 行和 `fail_list` 段。kernel 模块（`result_parser=ltp`）：无独立执行结果块（与 pkgserver 等一致，日志在下方"日志"段统一展示）。无 case 结果时显"无执行结果"。右栏下方分两段：**"日志"段**展示 `module_log` 类型 artifact 链接；**"pkg_manage_folder"段**展示 `pkg_folder` 类型 artifact 链接，点击进入文件夹浏览页。

`GET /pipelines/run-jobs/{id}` 返回 `error_code`、`error_message`、`task_events`（完整执行阶段时间线）、`case_runs`（本批次结果，含 `stdout_summary`/`stderr_summary`）、`rerun_candidates`（根用例全集的最新事实，含最新执行批次）、`logs`（artifact 列表含 `artifact_type`/`artifact_name`）。对 `artifact_name` 含 `pkgmanage-details`、`pkgcmd`、或 `update_list` 的 `module_log` artifact，API 同时返回 `content` 字段（全文文本，超 1MB 截断），前端直接渲染无需额外请求。前端按 `artifact_type` 和 `artifact_name` 分派渲染。

`GET /pipelines/run-jobs/{run_job_id}/case-runs/{case_run_id}/mugen-log`：按 case_run 的 `suite_name`/`case_name` 在 `pkg_folder`（`artifact_name` 以 `logs` 结尾）中查找匹配的 mugen 日志文件，返回 `{content, file_path, files, run_id, artifact_id}`（首个文件内容 + 全部匹配路径）。无匹配返回 404。多文件时前端通过 `readFolderFileApi` 切换。

`POST /pipelines/run-jobs/{run_job_id}/rerun` 接受 Case Run ID 列表，校验来源是链上最新终态、所选项
是各根 Case Run 在链上的最新事实且状态为 `passed`/`failed`/`error`/`timeout`、具有 suite/case 和
可复用根 EnvSet；允许一次选择分布在首次执行和不同历史重跑批次中的最新事实。后端在
创建前原子校验资源未释放、租约有效、节点可达、共享环境没有活动重跑或销毁；条件变化返回 409，
不创建半成品 RunJob。所有已登录用户均可调用。创建成功返回 `201` 与新 RunJob 标识（含
`rerun_chain`、`rerun_attempt`）。

`GET /pipelines/run-jobs/{id}` 返回 `can_rerun` 和 `rerun_unavailable_reason`。重跑活动期间，用例重跑
和环境销毁都不可用。链内共享环境销毁按 resource 去重，实际资源只销毁一次。

日志收集路径包含 RunJob/Test Job ID，保证每个 artifact 的物理文件独立。重跑前把所选 case 的远端
旧输出移动到执行批次归档目录，新 artifact 只收集本批次结果；已收集的来源 artifact 不更新或删除。

### 5.5 日志独立页

路由 `/pipelines/runs/:id/logs/:artifact_id`。页面秒开（下载按钮立即可用、不预载内容）；内容按需加载（点"查看内容"才 fetch 1MB 截断内容 + 渲染行号）；`/download` 端点返回全文（`FileResponse` 流式，不截断）。不做实时日志流，手动刷新。

### 5.5b Mugen 日志页（按 case）

路由 `/pipelines/run-jobs/:id/cases/:caseRunId/log`。展示该 case_run 对应的 mugen 日志文件内容（从 `pkg_folder` 的 logs 目录按 `{suite}/{case}/` 匹配）。带行号、下载按钮、多文件时展示文件选择器。无日志时显示空状态。

文件夹浏览路由 `/pipelines/runs/:runId/logs/:artifactId/folder`。用于 `artifact_type="pkg_folder"` 的目录 artifact：列出目录下全部文件（递归），点击文件名跳转该文件的内容视图（复用日志独立页渲染，但通过 `GET /pipelines/runs/{run_id}/logs/{artifact_id}/files?path=...` 读取单文件内容）。不做目录树折叠，扁平列表即可。

### 5.6 模块模板管理

支持模块模板列表展示、编辑（pre_env_script、rerun_env_script、post_env_script、mugen_exec_command 等代码编辑框）、新增。`rerun_env_script` 只在用例重跑的复用 EnvSet 中运行，首次执行不运行。模板按 `pipeline_type` segmented filter 划分（默认选 "update"）；后端 `list_module_templates` 加 `pipeline_type` 过滤参数。

A 类流水线（update）的 6 个 seed 模板 `pipeline_type="update"`；B 类（release 等）的模板由 `_find_or_create_suite_template(db, suite, pipeline_type=config.pipeline_type)` 在触发时自动创建（`name={pipeline_type}-{suite}`，空脚本），用户在触发时透明复用。所有模板平等可编辑——`find_or_create_suite_template` 复用现有模板，用户编辑过的内容在下次触发时保留。

`TestModuleTemplate.suite_name` 字段是框架无关的 suite 标识（mugen 框架下解释为 mugen suite 名，未来非 mugen 框架的 executor 自己解释）。

### 5.7 流水线类型管理

类型由 `pipeline_types` 表注册，`GET/POST/DELETE /pipelines/types` API 保留；类型选择入口在"测试模块模板"创建表单的 `pipeline_type` 下拉（数据来自 `GET /pipelines/types`）。前端不再提供独立"流水线类型"页面。

- `is_system=True` 的系统类型（update/release）由 seed 管理，API 不可删除。
- `is_system=False` 的类型：有 `pipeline_configs` 引用时删除返回 409 + 引用数量，无引用时硬删；可编辑 `display_name` 和 `default_config`。

### 5.8 流水线配置详情页

路由 `/pipelines/configs/:id/executions`。单页上下结构：

- 上半：config 元信息卡片（`name` / `pipeline_type` / `dist` / `image_round` / `versions` / `archs` / `test_framework` / `config_data` 摘要）+ 操作按钮区（触发新执行 / 编辑配置 / 删除配置）。
- 下半：该 config 的 `pipeline_executions` 表格（`triggered_at` / `status` / `versions` / `archs` / `triggered_by` / actions），按时间倒序，分页 20/页。
- 点行 → `execution-detail.vue`。
- "删除配置"按钮在 config 有 executions 引用时弹提示"请先清理 X 条历史执行"，并滚动到 executions 表方便用户操作。
- 仅 `ADMIN` 可见删除按钮和触发新执行按钮；`TSE`/`TE` 可读元信息和 executions 列表。

### 5.9 全局"近期执行" Tab

`index.vue` 的全局 executions Tab 改名"近期执行"，只展示最新 20 条作为活动 feed。承担"看最新动态"职责；找特定 config 历史走 per-config 页（§5.8）。

### 5.10 流水线配置列表

`index.vue` 的配置 Tab（流水线页默认 Tab）。表格列：配置名称 / 类型 / 测试版本 / 架构 / 模块 / **最新执行结果** / 操作（触发·编辑·历史）。

`GET /pipelines/configs` 每条 config 带最新一次 execution 摘要（`latest_execution: {id, status, triggered_at}`，按 `triggered_at` 降序取最新一条、含运行中；无执行为 `null`）。最新执行结果列：有 execution 则状态 Tag（`statusColor`/`statusLabel`，同 §5.2 矩阵色）+ 下方触发时间；无 execution 显"未执行"灰 Tag。该列只读、不跳转——下钻走操作列"历史"按钮到该 config 的 executions 详情页（§5.8）。

## 6. 调度与收尾

### 6.1 调度

手动触发为主。保留 `POST /api/v1/pipelines/trigger` API 接口供外部脚本自动调用。radiaTest 不做主动监测。

### 6.2 状态查询

`GET /pipelines/executions/{id}/summary` read-time 聚合所有 RunJob 状态/计数/日志/节点 IP。`GET /pipelines/runs/{id}/logs` 列 TestLogArtifact。`GET /pipelines/runs/{id}/logs/{artifact_id}` 经 `read_run_log_content` 返回文件内容（超 1MB 截断，用于页面展示）。`GET /pipelines/runs/{id}/logs/{artifact_id}/download` 流式返回全文（`FileResponse`，不截断，用于下载）。`GET /pipelines/runs/{id}/logs/{artifact_id}/files?path=...` 用于 `pkg_folder` 类型目录 artifact：不带 `path` 时返回文件列表，带 `path` 时返回单文件内容（路径穿越防护：resolved path 必须在 artifact 目录内）。

### 6.3 收尾

`POST /pipelines/executions/{id}/destroy-envs`（admin-only）发版后人工统一销毁：遍历该 Execution 所有 RunJob 的 TestJob 的 `env_set.nodes`，VM 走现有 VM 释放链路，物理机释放租约。不改 RunJob/Execution 状态（只清环境）。Execution 详情页顶部展示"销毁环境"按钮（admin-only，确认弹窗）。卡死 RunJob：人手动重启环境上去检查（`keep_env` 的目的）；状态 read-time 诚实显示 `running`/`超时`，不引入 abandon 端点。

## 7. API 清单

| 端点 | 方法 |
| --- | --- |
| `/pipelines/types` | GET / POST / DELETE |
| `/pipelines/types/{id}` | PUT |
| `/pipelines/frameworks` | GET |
| `/pipelines/module-templates` | GET / POST |
| `/pipelines/module-templates/{id}` | PUT |
| `/pipelines/configs` | GET / POST |
| `/pipelines/configs/{id}` | PUT / DELETE |
| `/pipelines/configs/{id}/executions` | GET / DELETE |
| `/pipelines/trigger` | POST |
| `/pipelines/executions` | GET |
| `/pipelines/executions/{id}` | GET / DELETE |
| `/pipelines/executions/{id}/summary` | GET |
| `/pipelines/executions/{id}/destroy-envs` | POST |
| `/pipelines/executions/{id}/runs` | GET |
| `/pipelines/runs` | GET |
| `/pipelines/runs/{id}` | GET |
| `/pipelines/runs/{id}/jobs` | GET |
| `/pipelines/runs/{run_id}/jobs/{job_id}/nodes` | GET |
| `/pipelines/runs/{id}/logs` | GET |
| `/pipelines/runs/{id}/logs/{artifact_id}` | GET |
| `/pipelines/runs/{id}/logs/{artifact_id}/files` | GET |
| `/pipelines/run-jobs/{id}` | GET |
| `/pipelines/run-jobs/{id}/rerun` | POST |
| `/pipelines/run-jobs/{id}/cancel` | POST |

`POST /pipelines/run-jobs/{run_job_id}/cancel` 仅 ADMIN 可调用：仅 `pending`/`preparing`/`running`
可受理并返回 `202`；`cancelling` 与终态返回 `409`；目标不存在返回 `404`；409 请求不产生新的取消副作用。

`PipelineTriggerRequest` 支持可选 `image_round` 覆盖参数（适用 release 等每次 RC 换轮的场景）；触发时若传则覆盖 config 级 `image_round`，否则用 config 级值。

`DELETE /pipelines/configs/{id}`：硬删，但有 `pipeline_executions` 引用时返回 409 + 引用数，用户必须先清理 executions（admin only）。

`DELETE /pipelines/executions/{id}`：删单个 execution，级联 runs/run_jobs 及其下全部
TestJob 与子记录（环境集、节点、case run、子用例结果、任务事件、日志产物登记；环境由
`destroy_execution_envs` 先行销毁）[admin only]。级联删除 TestJob 是为消除孤儿任务
积压的根因，见 [ADR 0050](../adr/0050-test-job-deletion-and-pipeline-cascade.md)。

`DELETE /pipelines/configs/{id}/executions`：批量删该 config 所有 executions，一次性事务，要么全成功要么回滚（admin only）。

`GET /pipelines/executions`：支持可选 `config_id` 过滤和 `limit` 参数；不传 `config_id` 时返回全局 executions（用于"近期执行" feed，默认 limit 20）。

## 8. update 流水线类型

`pipeline_type = "update"`。首个流水线类型，对 openEuler update 版本执行 6 个测试模块。

### 8.1 case_filter 四分派（case 选择策略）

- `none` → `select_cases(suite=模板.suite_name, case_names=None)`。
- `repodata_packages` → `repodata.fetch_update_packages`（用 `settings.vm_openeuler_update_repo_root` 作为 repo 基址，不读 config_data，解析 update 仓库 `repodata/primary.xml.gz` 获取源包列表）+ `case_planner.plan_cases`（package→suite_name 匹配）→ `both` RunJob 在 builder 中按 VM/physical 用例创建对应 EnvSet；no_case 包建 `NO_CASE` 状态的 TestCaseRun（看板展示"应测 N / 实测 M / 未找到用例 K"）。`case_planner` 保持 pkgcmd/pkgunion 复用，不被强行泛化。pkgcmd/pkgserver/pkgunion 配置编辑界面可选"是否执行物理机用例"（per-module flag `pkgcmd_physical_enabled`/`pkgserver_physical_enabled`/`pkgunion_physical_enabled`，默认 true，存 config_data；总开关 UI 联动三个 per-module）；关掉 → builder 照建 physical env_set（可见、`NOT_EXECUTED` 标记、不建 node），`execute_env_set` 跳过 NOT_EXECUTED env_set（无机、不跑 case）。kernel（physical-only 模块）不受此开关影响。
- `repodata_union` → `fetch_update_packages` + `plan_cases`（repodata 路）与 `fetch_service_packages` + `oe_test_<type>_<name>` case_name 匹配（service 路）的**并集**，按 `(suite_name, case_name)` 去重——两路重叠的 service 用例只执行一次；no_case 口径沿用 repodata 路；`update_packages` 返回两路包名并集（供 pre_env 补装 update 轮新增包）。pkgunion 专用（[ADR 0047](../adr/0047-pkgunion-module.md)）。
- `service_test_cases` → `fetch_service_packages`（用 `settings.vm_openeuler_update_repo_root`，解析 binary repo 的 `filelists.xml` 找 systemd 服务文件）→ 构造 `oe_test_<type>_<name>` → 查 `MugenCase` 表匹配 → 按 env_type 拆分（跟 pkgcmd 对称，在 builder 阶段完成，不需机器）。

**pkgunion 互斥校验**：update 配置保存（create/update）时校验 `module_template_ids` 对应模板名——pkgunion 与 pkgcmd/pkgserver 不得同时勾选（并集重叠，同勾会让重叠用例在新老模块间重复执行），违例返回 422。不含 pkgunion 时 pkgcmd+pkgserver 同勾维持合法（存量配置不动）。

危险用例过滤（[ADR 0043](../adr/0043-dangerous-case-filter-for-pipelines.md)）：全部四条 case_filter 分派路径（none/repodata_packages/repodata_union/service_test_cases）解析出的用例，在 builder 生成 EnvSet 前统一过危险用例识别——命中名字规则（initrd 前缀与关机/重启/休眠类单元的精确名单）、同步脚本扫描标记或内置兜底名单任一即被拦下。被拦用例不生成 TestCaseRun、不出现在用例统计中，builder 写一条 `cases_filtered` 事件（含数量与用例名及原因）到 TestJob 事件流留痕；rerun 链路复用来源执行记录，不做该过滤。手工测试任务暂不接入（识别模块为公共实现，后续接入为加法）。

### 8.2 6 个模块定义

#### 8.2.1 docker

`suite_name=smoke`，`env_set_num=1`，`node_num=1`，`case_filter=none`，`env_type=vm`，`result_parser=mugen_results`，`mugen_exec_command=docker exec -u root openEuler_test bash -c 'cd /home/mugen && bash mugen.sh -f {suite} -r {case} -x'`。pre_env_script：装 Docker（`docker-engine-*18.09*`）→ 配置 devicemapper + RAMDISK → 下载 openEuler docker 镜像（`121.36.84.172`）→ `docker load` → 创建容器（`/bin/bash`）→ 拷 host `openEuler.repo` 到容器 + `dnf makecache` → 容器内 `dnf install` 依赖 + `ldconfig` → 停容器改 entry 为 `/sbin/init` → 启容器 + 验证运行 → clone mugen（`atomgit.com`）→ `docker cp` 进容器 → `mugen.sh -c` → `dnf check-update`。post_env_script：从容器拷 logs/results/check_update.log 到 `/opt/docker-logs/`。`check_update.log` 作普通 artifact（`artifact_type=check_update_log`）不解析子用例。

#### 8.2.2 kernel

`suite_name=ltp`，`env_set_num=1`，`node_num=1`，`case_filter=none`，`env_type=physical`（kernel 只物理机），`result_parser=ltp`，`mugen_exec_command=None`。环境建立额外步骤（pre_env 之前）：`create_env_node_physical` 在 PXE 重装成功后、跑 mugen 前，对 kernel 模块（`template.name=="kernel"` 且 `os_version` 不以 `-64k` 结尾）调 `install_latest_kernel_via_ssh`——取最新 update 轮（`list_update_dirs(...)[:1]`）写 `[openEuler_update_<round>]` repo → `dnf install -y kernel` → `reboot` → 等 SSH 回来 → `uname -r` 写 `resource.kernel_version`，记 `kernel_latest_installed` 事件；失败记 `kernel_latest_install_failed` + 标 `resource.management_status=DISABLED`（退出轮转）+ node `ERROR` + raise `TestJobExecutionError("kernel_install_failed")`，留 GA 内核、不跑 LTP（[ADR 0026](../adr/0026-kernel-module-latest-update-kernel.md)）。`-64k` 变体不触发本步骤，仍走 [ADR 0024](../adr/0024-vm-64k-kernel-post-processing.md) 的 64k 路径。事件经 `record_test_job_event` 落 job 事件流。pre_env_script：开头嵌入 `UPDATE_REPO_SETUP`（公共换源脚本，取最新 `update_YYYYMMDD/` 目录写入 `/etc/yum.repos.d/`；`dnf makecache` 重试 3 次应对 VM 公网 DNS 瞬时抖动致元数据下载失败）→ modprobe vsock_loopback → 调内核参数 → LTP_TIMEOUT_MUL=5 → 启用 journald 持久化（`mkdir /var/log/journal` + 重启 journald，机器侧日志跨 reboot 留存，支撑挂死取证）→ patch cpufreq_boost.c (aarch64) → irqbalance + setenforce → patch oe_test_ltp.sh 不删 /opt/ltp。所有内核参数/sys 路径命令带 `|| true` 容错（不同内核版本路径可能不存在）。post_env_script：拷 LTP results → awk 提取 failed cases → 拷 mugen logs/results + ltp.txt（保留 .txt，不 rename）。子用例解析：`parse_ltp_log` 提取 TPASS/TFAIL。

#### 8.2.3 pkgcmd

`suite_name=cli-test`，`env_set_num=1`，`node_num=1`，`case_filter=repodata_packages`，`env_type=both`，`result_parser=pkgcmd`，`mugen_exec_command=None`。pre_env_script：开头嵌入 `UPDATE_REPO_SETUP` → mount --make-rshared → sysctl → install polkit。post_env_script：遍历 `results/<pkg>/succeed|failed|skipped` → 统计到 `pkgcmd.log` → 拷 mugen logs/results。子用例解析：`parse_mugen_results_dir`。物理机执行模式用于对应 physical EnvSet。

#### 8.2.4 pkgmanage

`suite_name=pkgmanager-test`，`env_set_num=2`，`node_num=2`，`case_filter=none`，`env_type=vm`，`result_parser=pkgmanage`，`mugen_exec_command=None`。总 VM 数：2 用例 × 2 节点 = 4 台/版本+架构。pre_env_script：开头嵌入 `UPDATE_REPO_SETUP` → aarch64 装 edk2/ovmf。post_env_script 日志格式参考 lkp-tests `mugen-oeupdate-pkgmanage`：`CASE` 从 `KRONOS_ENV_SET_INDEX` 派生（`printf "%02d" "${KRONOS_ENV_SET_INDEX}"`，set_index 1-based），日志头 `${KRONOS_OS_VERSION}-${KRONOS_ARCH}-pkgmanage-0${CASE}`；头后 grep 用例日志的两架构包数检查结果——有差异才出一行 `==`（差异不在白名单 `ERROR` → `== two architectures are not equal in number`；差异在白名单 `INFO All diff packages in whitelist` → `== two architectures diff in whitelist, pass`；无差异不出）；再 grep `${OET_PATH}/logs/pkgmanager-test/oe_test_pkg_manager0${CASE}/*.log` 的 `test -n` 行（带 `+ `前缀，是 bash `set -x` trace 输出，非包名）；`fail_list` 段从 `/home/pkg_manager_folder/*fail_list` 收集，无则输出 `no fail_list`，有则逐文件列出 `prefix:` + 内容并拼接 `all_contents`。post_env_script 同时把 `/home/pkg_manager_folder` 拷贝到 `/opt/pkgmanage-logs/pkg_manager_folder-0${CASE}`，拷贝 `${OET_PATH}/logs` 和 `${OET_PATH}/results` 到 `/opt/pkgmanage-logs/`，日志自汇集时 `scp -r` 拉取为 `artifact_type="pkg_folder"` 目录 artifact。子用例解析：`parse_pkgmanage_log`——只从 `fail_list` 段提取失败包名，每个失败包 `status=failed`；无 `fail_list` 段时不产生子用例（全部隐含通过）。pkgmanage 是唯一 `env_set_num=2` 模块，2 个 env_set 并行执行，各产一份 `pkgmanage-details.log` 和一份 `pkg_manager_folder-0${CASE}` 目录，artifact_name 按 multi_env 规则带 `env{index}-` 前缀避免重名。

#### 8.2.5 pkgserver

`suite_name=service-test`，`env_set_num=1`，`node_num=1`，`case_filter=service_test_cases`，`env_type=both`，`result_parser=pkgserver`，`mugen_exec_command=None`。builder 解析 update binary repo 的 `filelists.xml` 找 systemd 服务 → 构造 `oe_test_<type>_<name>` → 查 `MugenCase` 表匹配 → 按 env_type 拆 VM/physical case_run。pre_env_script：source mugen `configure_repo.sh` → `package_install()` 装包（生成 `update_list`/`install_log`）→ `search_all_services()`（生成 `failed_install`/`all_services`）→ `check_new_service()` 测无专用用例的服务（输出到 `new_service_test.log`，测试结果不影响 pre_env 退出码——mugen `test_reload()` 对异常状态服务会 `return 1`，加 `|| true` 避免误报 `hook_failed`）。分析文件写到 `/opt/pkgserver-logs/`。post_env_script：`clean_up_env()`（停服务+卸包，生成 `remove_log`）→ 重装 openssh-server + 重启 sshd（`clean_up_env` 卸包含 openssh-server，恢复后 `_self_collect_logs` 才能 SSH 拉日志）→ 扫全部 `results/` 目录生成 `pkgserver-details.log` → 拷 mugen logs/results。子用例解析：`parse_mugen_results_dir`。物理机执行模式用于对应 physical EnvSet。

#### 8.2.6 pkgunion

`suite_name=cli-test`，`env_set_num=1`，`node_num=1`，`case_filter=repodata_union`，`env_type=both`，`result_parser=pkgunion`，`mugen_exec_command=None`。pkgcmd 与 pkgserver 的用例并集模块（[ADR 0047](../adr/0047-pkgunion-module.md)），与两老模块互斥（配置保存时校验）。builder 两路解析按 `(suite, case)` 去重（§8.1）；`update_packages` 为两路包名并集。pre_env_script（无 strict mode，同 pkgserver——mugen 库函数不兼容 set -u/-e）：开头嵌入 `UPDATE_REPO_SETUP` → `dnf update -y` 全量更新（失败显式 `exit 1`，fail-fast；**不 reboot**——运行旧内核+新 userland，最新内核由 kernel 模块在物理机单独覆盖）→ pkgcmd 环境位（`mount --make-rshared` + sysctl userns + polkit）→ source mugen 库 → `update_list` 生成（repo 已由 `UPDATE_REPO_SETUP` 配好，不再调 `cfg_*`）→ 按 `KRONOS_TEST_PACKAGES`（builder 注入的并集包名）补装（全量更新后已装的 no-op，实际装 update 轮新增包）→ 服务发现 → `select_services` 分类 → `check_new_service` 冒烟无专用用例的服务（`|| true`）。分析文件写到 `/opt/pkgunion-logs/`。post_env_script：`clean_up_env()`（停服务+卸包，卸载是服务测试动作的一部分）→ 重装 openssh-server + 重启 sshd → 扫全部 `results/` 生成 `pkgunion-details.log` → 拷 mugen logs/results。子用例解析：`parse_mugen_results_dir`（`result_parser=pkgunion` 接入解析/逐 case 收集/rerun 归档三处分发表）。物理机用途标记 `pkgunion-update`。no_case/包行展示为状态驱动，与 pkgcmd 同款。

## 9. release 流水线类型（B 类 direct_run）

**用例选择与物理机开关**：配置卡片支持「全选用例」（一键显式选中所有 suite 的全部 case，`case_names: []` 后端等价全选）。`config_data.release_physical_enabled` 控制物理机用例执行与否（默认关闭）：

- 关闭：物理机用例进入独立物理环境集，标记 NOT_EXECUTED（不建节点、不租用物理机），页面上可见为"未执行"。
- 开启：为物理机用例创建可执行物理环境集（node_num = 物理用例最大节点数），执行期按物理环境流程租用物理机。

VM 用例不受该开关影响。release 模板 `env_type = both`（按 env_type 拆分环境集）。

`pipeline_type = "release"`，`strategy_kind = "direct_run"`，`test_framework = "mugen"`。Seed 系统类型（`is_system=True`），前端不可删。

### 9.1 case 选择策略

case 级筛选：用户在 `pipeline_configs.config_data.case_selections` 填一组 `{suite_name, case_names}`（`case_names` 为该 suite 下选中的 case 名列表，空列表等价于该 suite 全选）。`suite_name` 来源于 `mugen_cases` 表的 distinct `suite_name`，`case_name` 来源于该 suite 下的 `mugen_cases.case_name`。每个 RunJob（per-arch）汇总全部 `case_selections` 的选中 case，用 `case_filter="none"` + `select_cases(selections=[...])` 仅执行选中的 case（跨 suite 共一套环境，不按 suite 拆分 RunJob）。

### 9.2 RunJob 形状

release 为单版本+单轮次配置（`versions` 列表长度固定为 1）。`DirectRunPipelineStrategy.plan_run_jobs` 为每个 `arch` 创建一个 RunJob（env_type 固定为 `vm`，不拆 vm/physical）。每个 RunJob 用单个 `release` 模板（`_find_or_create_release_template(db, pipeline_type)`，name=`{pipeline_type}`，`pre_env_script=""`，`post_env_script=` 默认日志拷贝脚本，`mugen_exec_command=None`，`result_parser="mugen_results"`），存于 `test_module_templates` 表，复用 update 模板的 builder 路径。

每个 RunJob 的 TestJob/env_set 跑**全部选中 suite 的 case**（跨 suite 共一套环境）。builder `_resolve_cases` "none" 分支汇总 `config_data.case_selections` 全部 suite 的选中 case 进一个 TestJob。env_set `node_num` = 全部选中 case 的 `node_num` 最大值（如 2 suite 共 10 case，其中 1 个需主从 2 节点 → 建 2 台 VM，全部 case 共享该 env_set），`env_set_num` = 1。builder 复用 `create_job_env_sets`/`distribute_bundles` 生成单个 env_set。多架构时各架构独立 RunJob/env_set，互不影响。

默认 `post_env_script` 把 mugen 原生 `${OET_PATH}/logs` 和 `${OET_PATH}/results` 拷贝到 `/opt/{template.name}-logs/`（=`/opt/release-logs/`），使通用 §4.8 自汇集（SSH 拉 `/opt/{template.name}-logs/*`）对 release 无需额外编排即可落盘日志；release 模板的 `post_env_script` 非空。

### 9.3 image_round 配置级

release 为单版本+单轮次配置，`image_round` 存于 `PipelineConfig.image_round`（配置级），触发无参数（不使用 `PipelineTriggerRequest.image_round` 覆盖）。新 RC 轮次由用户编辑配置的 `image_round` 实现；配置可重复触发。update 仍保留触发级覆盖语义不变。

### 9.4 看板展示

`execution-detail.vue` 矩阵列 = `moduleList × arch`；release 单模板 → `moduleList=[release]`，故矩阵为一组 `release × arch` 子列（按架构分列，不再 per-suite）。`run-job-detail.vue` 的用例列表仍按 `case_run.suite_name` 分组（跨 suite 共一个 RunJob，多个 suite 分组并列）；隐藏"模块脚本"区域（direct_run 模板的 `post_env_script` 为默认日志拷贝脚本、非用户模块配置，不展示），其余结构（子用例 / 日志列表）完全复用。

### 9.5 内核变体

release 配置可选一个内核变体：`config_data.kernel_variant`（dailybuild `*-with-kernel-*` 变体段，来自 `list_kernel_variants(os_version, round, arch)`）或 `config_data.kernel_rpm_url`（手动 RPM URL，HTTP/HTTPS 且以 `.rpm` 结尾）。两者互斥（设其一则另一为空），均可空（不换内核）。选定的变体/URL 在 builder 阶段快照到 `TestJob.pipeline_extras`（JSONB，键 `kernel_variant`/`kernel_rpm_url`），`create_env_node_vm` 从 `job.pipeline_extras` 读取并透传给 `VMRequestCreate`，由既有 `process_vm_request` → `apply_custom_kernel` 在 VM 创建后换内核+重启（与 VM 申请页同一链路）。update 的 `pipeline_extras` 为 NULL，`create_env_node_vm` 透传 NULL，行为不变。后续新流水线的类型专属执行参数均入此 JSON，不再逐类型加列。

多架构时变体为单一共享选择：前端取各选中架构可用变体的交集供选择；交集为空则不能选变体（留空不换内核）。变体应用于该配置的全部 VM。

## 10. 流水线类型管理

前端独立页 `/pipelines/types`，仅 `ADMIN` 可写：

- **列表**：所有 `pipeline_types` 记录，展示 `name`、`display_name`、`strategy_kind`、`test_framework`、`is_system`、`default_config`。
- **新增**：填 `name`（唯一）、`display_name`、`strategy_kind`（固定 `direct_run`，A 类不可在前端创建）、`test_framework`（从 `GET /pipelines/frameworks` 拿）、`default_config`（JSON，对 mugen framework 可填 `default_suites`）。
- **编辑**：`is_system=True` 类型不可编辑核心字段；`is_system=False` 类型可编辑 `display_name` 和 `default_config`。
- **删除**：`is_system=True` 拒删；`is_system=False` 有 `pipeline_configs` 引用时返回 409，无引用时硬删。

## 11. 验收标准

### 11.1 通用框架

- [ ] 数据模型：9 张新表（含 `pipeline_types`）+ `pipeline_run_jobs.test_job_id` 关联和 nullable `task_id` + `test_jobs` 扩展（`physical_usage_scenario`/`mugen_exec_command`/`keep_env`/`result_parser`/`pipeline_extras`）+ `TestCaseRunStatus.SKIPPED` 档 + 迁移。`pipeline_configs.pipeline_type` 逻辑引用 `pipeline_types.name`，不加物理 FK。
- [ ] `pipeline_types` CRUD API + `GET /pipelines/frameworks` API + 流水线类型管理 UI（admin-only）。
- [ ] `registry.get_pipeline_strategy` 按 `pipeline_types.strategy_kind` 分派到 `UpdatePipelineStrategy` 或 `DirectRunPipelineStrategy`。
- [ ] 模块模板 CRUD API + 模板管理 UI。
- [ ] Pipeline 配置 CRUD API（含 `pipeline_type` 逻辑引用 `pipeline_types.name`）。
- [ ] 触发 API 创建 Execution + Run + RunJob 空壳（status=pending）+ 为每 RunJob 发 `run_pipeline_run_job` Celery 任务；支持 trigger 级 `image_round` 覆盖。
- [ ] `run_pipeline_run_job`：按 case_filter 建 TestJob（绕开 create_test_job）→ 复用 `process_test_job` → 更新 RunJob 状态 → finally 自汇集日志。fail-safe 不 raise。
- [ ] `execute_env_set` 按 `env_set.env_type` 切 `create_env_node_physical`/`create_env_node_vm`；NodeInfo 在建完节点后写入。
- [ ] `process_test_job` 在 `keep_env=True` 时跳过 cleanup。
- [ ] `run_case` 挂 HangDetector（30s 超时，5 次失败阈值）+ 写 `/tmp/kronos-current-case` + 挂死 console_capture + 标 ERROR + 不 break（catch + continue + 连续 3 个熔断）+ 其他 env_set 继续。
- [ ] `run_case` 正常结束后按 `result_parser` 调解析器写 TestCaseRunDetail。
- [ ] Run/Execution 状态 read-time worst-wins 推算；Worker 中断或 started 超过 15 小时的 RunJob、关联 TestJob 和执行中 VM 申请按恢复规则收敛为错误终态。
- [ ] 共享卷挂载 worker（`/data/test-logs`）+ LogCollector 写入；文件（`scp` + `store_file_artifact`）和目录（`scp -r` + `store_dir_artifact`）双模式自汇集。
- [ ] Execution 总矩阵页（行=版本/列=模块×架构；each `both` module has one aggregate RunJob block；状态+计数、超时标色、read-time 聚合）+ Run 页（单版本矩阵+IP Tag）+ RunJob 详情页（主从：用例列表+子用例+日志/文件夹链接同位置排列）+ 日志独立页（全屏+行号+下载+截断）+ 文件夹浏览页（扁平文件列表→单文件内容）。看板按 `strategy_kind` 条件渲染，update 显示模块脚本/exec_command，direct_run 隐藏。
- [ ] 日志 API：`GET /runs/{id}/logs`、`GET /runs/{id}/logs/{artifact_id}`、`GET /runs/{id}/logs/{artifact_id}/files`、`GET /executions/{id}/summary`。
- [ ] `POST /executions/{id}/destroy-envs`（admin-only）。
- [ ] 导航/标题"流水线"，路由 `/pipelines/*`。

### 11.2 update 流水线类型（A 类代码驱动）

- [ ] 6 模块模板（docker/kernel/pkgcmd/pkgmanage/pkgserver/pkgunion）含 pre_env_script / post_env_script / mugen_exec_command。
- [ ] case_filter 四分派（none/repodata_packages/repodata_union/service_test_cases）；pkgcmd repodata + case_planner + `NO_CASE`；pkgserver repodata filelists + MugenCase 匹配；pkgunion 两路并集按 `(suite, case)` 去重 + 包名并集。
- [ ] pkgunion pre_env 换源后 `dnf update -y` 全量更新（fail-fast，不 reboot）。
- [ ] update 配置保存时 pkgunion 与 pkgcmd/pkgserver 互斥校验（422）。
- [ ] `result_parser=pkgunion` 接入子用例解析、逐 case 收集、rerun 归档三处分发表。
- [ ] pkgcmd/pkgserver/pkgunion 的 `both` RunJob 内 physical EnvSet 走物理机执行模式。

### 11.3 release 流水线类型（B 类数据驱动）

- [ ] Seed `release` 类型（`strategy_kind=direct_run`, `framework=mugen`, `is_system=True`）。
- [ ] release 配置为单版本+单轮次（`versions` 长度 1，`image_round` 配置级）；触发无参数。
- [ ] `DirectRunPipelineStrategy.plan_run_jobs` 为每个 arch 创建 RunJob（单版本约束）；每架构一套环境跑全部选中 suite 的 case。
- [ ] `_find_or_create_release_template` 建单个带默认 `post_env_script`（日志拷贝）的 release 模板。
- [ ] builder `none` 分支 direct_run 汇总 `config_data.case_selections` 全部 suite 的 case 进一个 TestJob；env_set `node_num`=max(全部选中 case node_num)，`env_set_num=1。
- [ ] `test_jobs` 加 JSONB `pipeline_extras`（nullable），builder 把 release 的 `kernel_variant`/`kernel_rpm_url` 快照入此 JSON；`create_env_node_vm` 从 `job.pipeline_extras` 读取透传 `VMRequestCreate` → `apply_custom_kernel`。update 的 `pipeline_extras` 为 NULL 不受影响。
- [ ] release 配置表单：cascading dist→os_version→round→多架构 checkbox→内核变体(dailybuild select XOR RPM URL)→case 选择器（左 suite 浏览、右"已选"视图：选 suite 默认全选 case，可展开精细取消、可整 suite 移除）。
- [ ] `GET /pipelines/mugen-suites` + cases 供选择器；多架构变体取交集。
- [ ] 前端可新增/删除 `is_system=False` 的 direct_run 类型；有引用时拒删返回 409。

### 11.4 配置删除与历史执行汇集

- [ ] `DELETE /pipelines/configs/{id}` 硬删，有 executions 引用时返回 409 + 引用数；admin only。
- [ ] `DELETE /pipelines/executions/{id}` 删单个 execution 级联 runs/run_jobs；admin only。
- [ ] `DELETE /pipelines/configs/{id}/executions` 批量删该 config 所有 executions，一次性事务；admin only。
- [ ] `list_pipeline_executions` 加 `config_id` 过滤参数 + `limit` 参数。
- [ ] 前端新页面 `/pipelines/configs/:id/executions` 单页上下结构（上半 config 元信息+操作按钮，下半 executions 表按时间倒序分页）。
- [ ] 配置列表行加"历史"按钮跳到新页面。
- [ ] 全局"执行记录" Tab 改名"近期执行"，限 20 条。

### 11.5 测试模块模板按类型划分

- [ ] `TestModuleTemplate` 加 `pipeline_type` 列（迁移）。
- [ ] `suite_name` 字段作为框架无关的 suite 标识（迁移 + 后端 + 前端 + 测试全改）。
- [ ] `_find_or_create_suite_template(db, suite, pipeline_type)` 接 pipeline_type 参数；模板 `name={pipeline_type}-{suite}`。
- [ ] `list_module_templates` 加 `pipeline_type` 过滤参数；`GET /pipelines/module-templates` 接 query 参数。
- [ ] 前端"测试模块模板" Tab 加 `templateTypeFilter` segmented control，默认选 "update"。
- [ ] 前端字段名全改（pipelines.ts / index.vue / detail.vue）。

### 11.6 不支持 / 延后

- 物理机 BMC IPMI serial console（留口子，实现延后）。
- 自动定时调度 / 主动监测 update 仓库（ADR 0032 已否）。
- 实时日志流（手动刷新）。
- `test_framework` 的前端 CRUD（保持代码注册，新增 framework 是开发行为）。
- AI 日志分析（后续 additive 集成，不改现有表/流程）。
- release 的物理机 RunJob / ISO-PXE 安装（单版本+qcow2+apply_custom_kernel 已覆盖当前 RC 测试场景；物理机/ISO 后续扩展）。
- release 的 `-64k` os_version 后缀路径（release 用 `kernel_variant` 字段，不用 `-64k` 后缀）。
