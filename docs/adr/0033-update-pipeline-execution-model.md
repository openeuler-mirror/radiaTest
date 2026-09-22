<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0033：Update 测试流水线执行模型

## 状态

已接受(Accepted)。

> `mugen_suite`、按 RunJob `env_type` 拆用例和 no_case=`SKIPPED` 的早期描述，已分别被 ADR 0012、ADR 0018 和 ADR 0037 取代；当前产品行为以 [Spec 0003](../spec/0003-test-pipeline.md) 为准。

## 背景

[ADR 0032](./0032-update-test-pipeline.md) 确立了 Pipeline 作为 TestJob 之上的编排层、模块模板、物理机执行模式、VM 全保留、挂死检测、子用例解析和看板等高层决策。但 ADR 0032 未定义执行模型的关键取舍：trigger 如何把 RunJob 变成可执行任务、复用还是绕开现有 TestJob 构造路径、状态如何聚合、日志如何汇集、挂死如何处理、收尾如何销毁保留的环境。

初版实现只建了 Execution/Run/RunJob 三层空壳记录，不建 TestJob、不发 Celery、不更新状态、不写 NodeInfo；`create_test_job` 的 `env_type=vm` 策略门把物理机路径堵死；`run_case` 没接 HangDetector / 当前 case 标识 / result_parser；日志汇集、共享卷、在线查看均缺。本 ADR 补充这些实现层取舍。

## 决策

### 1. 复用执行机器 + 绕开构造机器

RunJob 的执行复用现有 `process_test_job` → `execute_env_set` → `run_case` 链路（已有 env_set/node/case_run/mugen_exec_command/超时/事件全链路）。`trigger_pipeline` 不调 `create_test_job`（其 `env_type=vm` 策略门和手动选 case 的 API 不适配流水线），改用 pipeline 专用 TestJob 构造函数，直接拿 case_planner / select_cases 产物 + 模板字段建 TestJob/EnvSet/Node/CaseRun，`env_type` 可为 `physical`。

不采用：给 Pipeline 单开执行链路——会复制 mugen 部署、env 文件、hook、超时、事件全链路，两链路以后要对齐维护。

### 2. 异步 per-RunJob 编排

trigger（HTTP）只建 Execution + Run + RunJob 空壳（`status=pending`），为每个 RunJob 发一个 `run_pipeline_run_job` Celery 任务，立即返回 Execution。`run_pipeline_run_job` 按 `case_filter` 建 TestJob（pkgcmd 在此拉 repodata）→ 调 `process_test_job`（复用）→ 更新 RunJob 状态 → finally 块自汇集日志。

**enqueue 必须在事务提交后**：trigger 先 `db.commit()` 持久化 Execution/Run/RunJob，再由 `enqueue_run_jobs` 投递 Celery 任务。理由：worker 用独立 DB session 查 run_job，若 enqueue 早于 commit，worker 在事务可见前消费 task 会查不到 run_job 而 `return`，导致 run_job 永远 `pending`（前端显示"等待"）。单个 enqueue 失败时标该 run_job 为 `error(queue_unavailable)` 并继续其余，不整体回滚——回滚会让已投递的 task 重蹈"查不到未提交 run_job"的覆辙。

不采用：
- 同步扁平——web 里同步拉 repodata 建所有 TestJob 再派发，任一版本 repodata 失败整次触发失败，web 干网络活。
- 异步 per-Run prep——多一层 prepare_pipeline_run 任务，prep 与 run 分两阶段、状态多一档。

### 3. case_filter 三分派，case_planner 保持 pkgcmd 专用

- `none` → `select_cases(suite=模板.mugen_suite, case_names=None)`（docker smoke / kernel ltp / pkgmanage pkgmanager-test）。
- `repodata_packages` → `repodata.fetch_update_packages` + `case_planner.plan_cases` → 按 RunJob.env_type 取 vm/physical 用例；no_case 包建 `SKIPPED` 状态的 TestCaseRun（看板展示"应测 N / 实测 M / 无用例 K"）。
- `service_test_cases` → `select_cases(suite="service-test", case_names=None)` 再按 env_type 滤成 vm/physical 两组。

> **已变更（ADR 0022）**：`service_test_cases` 改为返回空 case 列表，case_runs 在 pre_env 后动态发现。pkgserver 不再走 `oe_test_service_restart` 的 case调case 模式。

`case_planner` 保持 pkgcmd 专用（package→suite_name 匹配 + no_case 跟踪），不被强行泛化。pkgmanage 的 01/02 拆 2 EnvSet 由模板 `env_set_num=2` + 现有 `distribute_bundles` 自然处理。

不采用：把 pkgserver 塞进 case_planner——service-test 是 suite 全量子用例按 env_type 拆分，不是 package 匹配，case_planner 是错配。

### 4. keep_env 独立字段，不复用 keep_failed_env

TestJob 新增 `keep_env`（布尔，默认 False）。pipeline builder 设 True → `process_test_job` 在 `keep_env=True` 时跳过 cleanup，VM/物理机全保留到发版后人工销毁。keep_env 环境的 VM 租约按 5 天设期（`expected_ends_at = created_at + 5 天`，见 Spec 0003 与 `test_management/envs/vm.py`），到期自动释放不作用于该保留窗口。`keep_failed_env` 语义不动（只保留失败的 env，既有非流水线 TestJob 行为不变）。

不采用：
- 复用 `keep_failed_env` 并放宽语义为"True ⇒ 全保留"——会改变现有非流水线 TestJob 行为（原只留失败 1 台变全留，资源泄漏），破坏 CONTEXT.md 对 `keep_failed_env` 的定义。
- 用 `pipeline_run_job_id` 是否非空隐式表达"全保留"——隐含约定易踩坑。

### 5. RunJob 状态机 4 档；Run/Execution 状态 read-time worst-wins 推算不存

RunJob：`pending → preparing → running → {succeeded | failed | error}`。
> 注：终态集合与状态机已被 [ADR 0030](0030-runjob-cancel.md) 与 [ADR 0031](0031-termination-convergence.md) 扩展（新增 `cancelled` 终态与 `cancelling` 中间态），现行终态集合为 `{succeeded, failed, error, cancelled}`；Worker 中断恢复语义见 [ADR 0035](0035-worker-interruption-recovery.md)（`cancelling` 且已请求取消收敛为 `cancelled`，其余标 `error`）。
- `pending`：trigger 建空壳，worker 未领。
- `preparing`：`run_pipeline_run_job` 领到并校验所属 Run、配置和模板。
- `running`：建 TestJob（拉 repodata / select_cases / 建 EnvSet/Node/CaseRun）并调用
  `process_test_job`（建 VM / mugen 执行）。repodata 失败 → `error`，不与"执行失败"混。
- `succeeded`：全部 case 通过；`failed`：有 case 失败/超时；`error`：环境/挂死/repodata/意外（对齐 CONTEXT.md 的 Error vs Failed）。enqueue 失败（`queue_unavailable`）也直接 `pending → error`，不进 `preparing`（见决策 2）。

Run/Execution 状态不存、不更新、不要 counter：API 读看板时实时从 RunJob worst-wins
推算（任一子非终态 → 父 `running`）。RunJob 保存 Celery task ID 并在 worker 领取时写
started 事件；Worker 启动时将旧的 `preparing/running` RunJob 标为 `error`，相关页面
读取时将 started 超过 15 小时的 RunJob 懒恢复为 `error(task_timeout)`。关联 TestJob 和
执行中的 VM 申请按 Worker 中断恢复规则收敛，不自动重放或清理远端环境。

不采用：
- counter rollup——丢失任务时 counter 卡死，需 abandon 端点兜底。
- chord 回调——依赖所有 body 任务完成，1-2 任务挂死则回调不触发。

### 6. 日志 per-RunJob 自汇集，无汇总 task

`run_pipeline_run_job` 在 finally 块（无论 success/fail/error/hang 都跑）SSH 到本 RunJob 控制节点拉 `/tmp/module-logs/*` → 逐文件 `store_artifact`。每个 RunJob 各自拉各自的，互不依赖——1-2 个挂死/丢失任务不影响其他 RunJob 日志落盘。挂死 RunJob：`console_diagnostic` 已抓；`/tmp/module-logs/` 拉取大概率失败（SSH 也死），best-effort 跳过。真正丢失的任务（worker 崩）不自动拉，但 VM 已保留（keep_env）→ 后续可手动补拉。

worker 容器加 `/data/test-logs` 共享卷；`LogCollector(base_dir=该路径)`。

"汇总" = Execution 总看板 API（`GET /executions/{id}/summary`）read-time 聚合所有 RunJob 状态/计数/日志/节点 IP，无汇总 task。

不采用：
- Execution 级单汇集 task（chord 回调）——1-2 任务挂死则全盘无日志，违背"看板不能少"。
- per-Run 汇集——N 个汇集任务 + 各自 chord/counter，复杂度高收益低。

### 7. 挂死处理：标 ERROR + 跳过本 env_set

`run_case` 挂 HangDetector（per-case start/stop，30s 心跳 SSH `echo ok`，3 次失败 90s 判挂死）+ 执行前写 `/tmp/kronos-current-case`（`suite/case`）。挂死时：`capture_vm_console_output`（SSH 到 `control.resource.host_resource_id` 宿主机跑 `virsh console/domstate`）→ 存 `console_diagnostic` artifact → 当前 case 标 ERROR → 本 env_set 剩余 case 全标 ERROR（同台 VM 死了没法跑）→ 跳过本 env_set 剩余 case → 其他 env_set 继续（不同 VM）→ TestJob 最终 ERROR（非 FAILED）。
> 注：挂死判定与中断语义已被 [ADR 0016](0016-hang-detector-self-heal.md)（5 次失败 + 计数熔断 + 1 次成功清零）、[ADR 0042](0042-physical-hang-confirmation-and-bmc-forensics.md)（判死前复核）与 [ADR 0044](0044-physical-hang-bmc-cross-check-watch-mode.md)（电源确认门/观察模式）逐层修订，以各后续 ADR 为准。

物理机 BMC IPMI console 暂留口子（`artifact_type=console_diagnostic` 存空 + 事件记录），实现延后。

不采用：
- 挂死后继续本 env_set 下一 case——死 VM 跑不了。
- 挂死标 FAILED——CONTEXT.md 明确环境问题 = Error，不是测试失败。

### 8. 收尾：仅 destroy-envs，无 abandon

发版后人工统一销毁：`POST /update-pipelines/executions/{id}/destroy-envs`，遍历该 Execution 所有 RunJob 的 TestJob 的 `env_set.nodes`，VM 走现有 VM 释放链路（`destroy_env_node_vm`），物理机释放租约。不改 RunJob/Execution 状态（只清环境）。

中断 RunJob 自动收敛为 `error`，环境仍按 `keep_env` 保留供人工检查；恢复只修正数据库
状态，不连接宿主机或销毁环境。

不采用：abandon RunJob 端点——保留环境就是为了人检查，挂死就重启环境手动查，不需要标 abandon。

### 9. docker 解析复用 mugen，pkgmanage 只从 fail_list 提取失败包

- docker：容器内跑 mugen smoke 套件，`result_parser` 走 `parse_mugen_results_dir`（标准 mugen results 目录），无特殊解析；`check_update.log` 作普通 artifact 不解析子用例。
- pkgmanage：`parse_pkgmanage_log(text)` 只从 `fail_list` 段提取失败包名，每个失败包 `status=failed`；无 `fail_list` 段时不产生子用例。mugen 日志中的 `test -n` 行是 bash `set -x` trace 输出（`+ test -n 'message'`），不包含包名，不用于提取被测包集合。日志头 `${KRONOS_OS_VERSION}-${KRONOS_ARCH}-pkgmanage-0${CASE}` 标 01/02 归属，`CASE` 从 `KRONOS_ENV_SET_INDEX` 派生。pkgmanage 是唯一 `env_set_num=2` 模块，2 个 env_set 在不同 VM 各产一份 `pkgmanage-details.log` 和一份 `pkg_manager_folder-0${CASE}` 目录，artifact_name 按 multi_env 规则带 `env{index}-` 前缀避免重名。

不采用：为 docker 单独写解析器——与 mugen results 同构，复用即可。不采用：从 `test -n` 行提取被测包名——mugen 日志中 `test -n` 是 bash trace 输出，不包含包名。

### 10. 流水线通用化：表/模型/API 去 update 前缀 + pipeline_type 字段

流水线是通用能力，update 是首个类型，后续可扩展 release 等。表 `update_pipeline_configs/runs/run_jobs` → `pipeline_configs/runs/run_jobs`；模型类 `UpdatePipelineConfig/Run/RunJob` → `PipelineConfig/Run/RunJob`；API `/api/v1/update-pipelines/*` → `/api/v1/pipelines/*`；前端路由 `/update-pipelines/*` → `/pipelines/*`，导航/标题"Update 流水线" → "流水线"。`pipeline_configs` 加 `pipeline_type` 字段（`update`/`release`/...，默认 `update`），配置列表按 type 分组/筛选。

这些表/路由/前端是本 feature 新建的，重命名不碰老代码。其余已通用命名的表（`pipeline_executions`/`pipeline_run_node_infos`/`test_module_templates`/`test_case_run_details`/`test_log_artifacts`）不动。

不采用：
- 保留 `update_` 前缀——把流水线框架绑死成 update 专属，阻碍 release 等后续类型接入，且与"流水线是通用能力"的领域定位冲突。
- 现在为 release 投机建专用表/字段——AGENTS.md 不默认加投机结构，release 真要做时按 `pipeline_type=additive`。

## 影响

- 后端 `modules/pipelines`：新增 pipeline TestJob 构造函数、`run_pipeline_run_job` Celery 任务、`GET /executions/{id}/summary`、`POST /executions/{id}/destroy-envs`。
- 后端 `modules/test_management`：扩展 `execute_env_set`（按 `job.env_type` 切 `create_env_node_physical`/`create_env_node_vm`）、`process_test_job`（`keep_env=True` 跳过 cleanup）、`run_case`（HangDetector + `/tmp/kronos-current-case` + result_parser 调用 + 挂死处理）。
- 数据库：`test_jobs` 加 `keep_env` 列；`TestCaseRunStatus` 加 `SKIPPED` 档；docker 模板 `result_parser` 改 `mugen_results`；流水线表去 `update_` 前缀（`pipeline_configs`/`pipeline_runs`/`pipeline_run_jobs`）+ `pipeline_configs` 加 `pipeline_type` 列。
- `deploy/docker-compose.server.yml`：worker 加 `/data/test-logs` 卷。
- 前端：导航/路由通用化（`/pipelines/*`、"流水线"标题）；Execution 详情页改总矩阵 + 新 RunJob 详情页（用例→子用例→日志）+ Run 页重做成单版本矩阵+IP + 日志在线查看独立页。
- 物理机 BMC IPMI console 延后实现。
- release 等其他 `pipeline_type` 后续 additive 接入，框架已通用化。

## 不采用方案（汇总）

- 扩展 TestJob 塞所有模块（ADR 0032 已否）。
- 给 Pipeline 单开执行链路（决策 1）。
- 同步扁平 trigger / 异步 per-Run prep（决策 2）。
- pkgserver 走 case_planner（决策 3）。
- 复用 `keep_failed_env` 全保留 / `pipeline_run_job_id` 隐式表达（决策 4）。
- counter rollup / chord 汇集 / abandon 端点（决策 5/6/8）。
- docker 单独解析器（决策 9）。
- 保留 `update_` 前缀 / 现在为 release 投机建专用结构（决策 10）。
