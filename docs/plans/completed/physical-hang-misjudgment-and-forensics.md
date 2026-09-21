<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# 物理机挂死误判治理与取证

## 背景

2026-09-09 prod 任务 10134（172.168.131.196 / openEuler 24.03-LTS-SP3 kernel）在
`ltp/oe_test_ltp` 启动 2 分 31 秒后被判 `vm_hang`（"VM/物理机挂死（心跳连续失败）"）。
取证结论（BMC SEL + 心跳节奏反推）：机器整机未重启、未断电，SSH 以秒拒方式不可达约
150 秒，恰在判定阈值（5 次 × 30s）压线上恢复，差 1 秒触发自愈失败。同机 9/5、9/8 的
vm_hang 事件 BMC 亦无重启记录，属 SSH 层失联被误标为整机挂死。物理机挂死路径无任何
现场取证（BMC 抓取一直延后），journald 易失，导致每次事件无法定界。

## 范围

1. **挂死判定复核确认**：`HangDetector` 连续失败达阈值后，不再立即 fire `on_hung`，
   先等一个 interval 复核一次；复核成功则计数清零继续执行，仍失败才判挂死。
   真挂死的杀掉延迟从约 300s 增至约 360s（超时型失败），可接受。
2. **心跳失败模式统计**：`_ssh_alive` 失败时分类计数（超时 / 拒绝 / 断连 / 其他），
   vm_hang 判定时把摘要拼进 `mark_case_execution_error` 的 detail，自动流入
   case_error 事件与任务错误信息，供人工区分"sshd 层抖动"与"整机失联"。
3. **物理机 BMC 取证**：`_capture_and_store_console` 的物理机分支改为抓取
   `ipmitool sel list` / `chassis status` / `sdr elist`，存为
   `bmc_diagnostic` artifact（与 VM 的 `console_diagnostic` 并列）。best-effort，
   BMC 不可达只记 debug 日志。这是 ADR 0032"物理机 BMC 对称处理"延后项的落地。
4. **journald 持久化**：`KERNEL_PRE_ENV` 追加创建 `/var/log/journal` 并重启
   journald，使用例执行期（含 LTP 中途触发 reboot）的机器侧日志可留证。

## 明确不做

- 不做挂死后自动断电重启/自动重试：物理机生命周期归调用方（既有 ADR 决策），
  真挂死时机器留给人工查现场。
- 不给单次心跳失败发 task_event（长任务抖动会刷屏）；自愈型瞬断的事后可见性
  依赖 bmc_diagnostic 与持久 journal，不足再议。
- 不调整 max_failures/interval 数值；不做失败模式分级判定（数据不足，先记录）。
- 不改 Docker/PkgCmd 等其他模块模板；不动 PXE 基础镜像。
- 前端无 artifact 类型硬过滤（已查证），不需要前端改动。

## 实施步骤

1. `test_hang_detector.py`：新增复核用例（阈值后复核成功→不判死且计数清零；
   复核失败→判死且 on_hung 仅一次），先失败后实现于 `hang_detector.py`。
2. `mugen_runner.py`：新增 `_HeartbeatStats`（分类 + summary），`_ssh_alive` 带统计，
   vm_hang detail 拼接摘要；配单测（分类/摘要 + run_case 端到端 detail 断言）。
3. `console_capture.py`：新增 `capture_bmc_diagnostics`；`mugen_runner.py` 物理机
   分支存 `bmc_diagnostic`；配单测（mock subprocess 与凭据解密）。
4. `pipelines/seed.py` `KERNEL_PRE_ENV` 追加 journald 持久化三行；配模板断言测试。
5. 新建 `docs/adr/0042-physical-hang-confirmation-and-bmc-forensics.md`（记录 9/9
   证据链、复核决策、不采用自动恢复）；更新 `docs/spec/0003-test-pipeline.md`
   §4.6（复核语义 + bmc_diagnostic）。

## 验证标准

- 上述单测先失败再通过；`./scripts/check.sh` 通过。
- 9/9 场景回归推演：outage ≈ 150s、阈值 150s 时，复核第 6 查（~180s）命中恢复，
  计数清零，case 不中断。
- vm_hang 事件 detail 含失败模式摘要；物理机挂死产生 `bmc_diagnostic` 产物。
