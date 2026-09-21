<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# 逐 case 日志原子上传

日期：2026-09-14
状态：进行中
关联：[ADR 0048](../../adr/0048-per-case-log-atomic-upload.md)、[Spec 0003 §4.8](../../spec/0003-test-pipeline.md)

## 范围

把"任务结束后统一拉取日志"改为"每个用例正常收敛后立即原子上传"，崩溃/取消/手动停止不再丢已执行用例的日志。

经 Grill 确认的七项决策：

1. **上传内容**：case 自身 mugen 执行日志目录 `/opt/mugen/logs/{suite}/{case}/` + results 桶目录（`/opt/mugen/results/{suite}/{succeed|failed|skipped}/{case}`）。
2. **时机与方式**：`run_case` 正常收敛后内联同步直传（`_per_case_collect_log` 同一插入点后），不引入后台线程；best-effort，失败不影响 case 结果。
3. **模块范围**：全部 mugen 模块；docker 模块先 `docker cp openEuler_test:/home/mugen/...` 到宿主机临时目录再 scp（两跳）。
4. **服务端布局**：增量写入共享目录 artifact——`{pipeline_log_dir}/{run_id}/{module}/{arch}/{run_job_id}/[env-{n}/]` 下 `logs/{suite}/{case}/` 与 `results/{suite}/{bucket}/{case}`；首个 case 落位时登记 `pkg_folder` 目录 artifact（名 `logs`/`results`，multi_env 带 `env{N}-` 前缀，与 `_self_collect_logs` 现有命名一致）。原子性：先 scp 到同级临时目录，`os.replace` rename 落位。`_self_collect_logs` 改补漏式：目录 artifact 已存在仍重拉全量（同名文件幂等覆盖），填补逐 case 上传失败留下的缺口。
5. **触发状态**：仅 passed / failed / timeout(exit 124) / skipped；挂死（EnvSetHangError）、SSH 传输失败、取消、15h 超时路径不上传（机器大概率不可达，console/BMC 取证已有 artifact 兜底）。
6. **跨模块上下文**：pipelines executor（`MugenFrameworkExecutor.prepare_and_execute`）构造纯 DTO（run_id/module_name/arch/run_job_id）传入 `process_test_job(job_id, case_log_context=…)`；test_management 侧进程内注册表按 job_id 存取（env_set 线程链不穿参），`run_case` 读取；无上下文（遗留 `run_test_job_task` 单跑入口）自然退化为不逐 case 上传。
7. **失败处理**：单次不重试，记 debug 日志继续下一个 case；完整性由结束补拉兜底。

## 明确不做

- pre_env / post_env / module 追加日志（`/opt/{module}-logs/{module}.log` 等）的逐段上传——仍由结束补拉统一处理。
- `vm_recovery_used` UnboundLocalError 修复（2026-09-14 job 10244/10245 发现的独立 bug，另行处理）。
- `test_case_runs.stdout_summary` 16KB 截断行为、前端与查看 API——零改动（`get_case_mugen_log` 按 job_id + `pkg_folder` + 名字以 `logs` 结尾查询，新布局天然命中）。
- 遗留 `run_test_job_task` 单跑入口不补上下文。

## 实施步骤

1. test_management 新增 `CaseLogContext` DTO + 进程内注册表（set/get/pop，线程安全）→ 失败测试。
2. `process_test_job` 接受可选 `case_log_context` 并注册/finally 注销 → 失败测试。
3. `mugen_runner` 新增逐 case 上传原语：scp logs+results 桶到临时目录、rename 落位、幂等登记目录 artifact；docker 路径分支 → 失败测试。
4. `run_case` 正常收敛路径调用上传原语（状态门控 passed/failed/timeout/skipped）→ 失败测试。
5. `_self_collect_logs` 改补漏式：目录 artifact 已存在时仍重拉 → 失败测试。
6. `MugenFrameworkExecutor.prepare_and_execute` 构造 DTO 注入 → 定向测试。
7. ADR 0048、Spec 0003 §4.8 同步。

## 验证标准

- 新增测试全部先失败后通过；既有 696 后端 + 99 前端测试不回归。
- `./scripts/check.sh` 全量通过。
- 模拟验证：job 中途异常终止时，已正常收敛的 case 日志已在服务端 artifact 目录可见。
