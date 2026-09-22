<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0048: 逐 case 日志原子上传

日期：2026-09-14
状态：已接受

## 背景

日志自汇集（Spec 0003 §4.8）是两道晚绑定关卡：case 原始日志要等 post_env（全部用例跑完）才从 `/opt/mugen/logs` 拷进 `/opt/{module}-logs/logs`，再等任务结束由 `_self_collect_logs` 在 finally 块统一拉回服务端。任务异常（如 job 10244/10245 的 `vm_recovery_used` UnboundLocalError）、用户手动停止、SSH 中断或机器被清理时，已执行用例的日志**全量丢失**——排障恰恰最需要日志的场景拿不到日志。

## 决策

每个用例正常收敛（passed/failed/timeout/skipped）后，由 runner **内联同步**把该 case 的 mugen 执行日志目录与 results 桶目录上传到服务端共享目录 artifact：

- **共享目录布局而非每 case 独立 artifact**：逐 case scp 进 `{pipeline_log_dir}/{run_id}/{module}/{arch}/{run_job_id}/[env-{n}/]` 下的 `logs/`、`results/` 目录，首个 case 落位时登记一次 `pkg_folder` artifact（命名与 `_self_collect_logs` 现有约定一致）。查看器 `get_case_mugen_log` 按 `job_id + pkg_folder + 名字以 logs 结尾` 查询，零改动命中。
- **原子落位**：先 scp 到同级临时目录，`os.replace` rename 进位——单个 case 的日志要么完整可见，要么不存在，无半传状态。
- **跨模块缝隙**：`run_case`（test_management）无 pipeline 上下文。由 pipelines executor 构造纯 DTO（run_id/module_name/arch/run_job_id）经 `process_test_job(job_id, case_log_context=…)` 可选参数注入，test_management 进程内按 job_id 注册存取（env_set 并行线程链不穿参）。依赖方向与现有 executor 调用一致（pipelines→test_management），无反向依赖；无上下文时退化为现状（仅结束统一拉取）。
- **结束补拉改补漏式**：`_self_collect_logs` 原逻辑"artifact 已存在即跳过"会让逐 case 上传失败留下的缺口永远补不上；改为目录已存在仍重拉全量（mugen 日志文件名含时间戳，同名文件幂等覆盖，不膨胀）。
- **失败处理**：逐 case 上传 best-effort 单次不重试；完整性兜底是结束补拉，两层职责分离（早传 vs 必达）。
- **docker 模块**：mugen 跑在 `openEuler_test` 容器内，先 `docker cp` 到宿主机临时目录再 scp（两跳），复用 post_env/rerun 归档的既有模式。
- **挂死/取消/传输失败路径不上传**：机器大概率不可达，空等 scp 超时只会拖慢挂死自愈链路；这些 case 由 console/BMC 取证 artifact 覆盖。

## 备选方案与不采用理由

- **后台线程异步上传**：不阻塞下一 case，但线程生命周期、乱序、崩溃丢尾部都是新复杂度；case 日志通常 KB~MB 级，同步传秒级完成，不值。否决。
- **被测机主动推送**：需向测试机下发服务端凭据或暴露上传端点，违反安全红线（应用凭据不出服务器）。否决。
- **每 case 独立 artifact**：一 case 一行 DB（systemd 模块 120 条），查看器搜索逻辑必须改，与结束补拉的布局分叉。否决。
- **module 追加日志逐 case 快照**：同一文件每 case 重复传整份（O(n²) 传输），非原子。否决；module 日志维持结束统一拉。
- **test_management 反查 PipelineRunJob 表取上下文**：产生 test_management→pipelines 反向模块依赖。否决。

## 影响

- `process_test_job` 签名增加可选参数（向后兼容，遗留 `run_test_job_task` 入口不传即退化）。
- `_self_collect_logs` 对已存在目录 artifact 的跳过行为变更为幂等重拉；手动触发 `collect-logs` 端点行为同步变化（多一次全量 scp，无语义变化）。
- 服务端磁盘占用不变量级：逐 case 上传与结束补拉写同一目录，无双份存储。
- pre_env/post_env 阶段日志仍是晚绑定（本 ADR 明确不做）；后续若需要可按同一 DTO 机制扩展。
