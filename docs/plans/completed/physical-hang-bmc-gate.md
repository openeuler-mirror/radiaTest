<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# 物理机挂死 BMC 交叉确认门（观察模式）

## 背景与根因

- 2026-09-10 kimariyb 任务 10230/10231（x86_64 物理 kernel，oe_test_ltp）在 LTP `oom01/oom02` 全局 OOM 风暴期间被误判 vm_hang。机器侧证据：BMC SEL 无重启记录、journal 单 boot 连续、SSH 在风暴结束后自愈、LTP 结果正常产出。
- 机制：oom0x 用例故意打满内存（实测 158–358GB anon 分配），控制面（SSH）分钟级失联；检测器按"连续失败 5×30s + 一次复核"判定整机挂死并杀任务，与真实状态不符。
- 历史对齐：挂死问题跟随 `oe_test_ltp` / `oe_test_socket_sssd-nss` 进入套件出现（kimariyb 8/29、prod 9/5 起），此前未发生。

## 方案（Grill 已确认）

1. BMC 交叉确认门：SSH 连续失败达阈值并复核确认后，若资源是有 BMC 配置的物理机，先查 BMC——chassis power status 为 on 且 SEL 中测试开始后无重启/断电记录 → 进入观察模式，不判挂死。
2. 观察模式：SSH 心跳维持 30s 不变；BMC 查询每 2–3 分钟一轮；SSH 恢复 → 记 info 事件、继续执行；BMC 报告重启/断电或电源 off → 判 vm_hang；BMC 查询失败不下结论、继续观察。
3. 兜底上限：观察 30 分钟（模块常量）仍未恢复或未确认 → 判 vm_hang。
4. 事件与取证：进入观察（warning）与出结论（恢复 info / 判挂死 error）时各抓一次 BMC 取证落盘，复用 console_capture.capture_bmc_diagnostics 通道；判挂死语义与现有 vm_hang 兼容。
5. 适用范围：仅"有 BMC 配置的物理机"；VM 与无 BMC 物理机维持现有判定（阈值 + 复核即判）。

## 明确不做

- `oe_test_socket_sssd-nss` 类失联机制不查不修（无证据，不预设 BMC 门能救它）。
- 不改心跳间隔与失败阈值参数；不做自动断电恢复。
- 不动用例过滤（危险用例过滤见 ADR 0043，与本方案互补；LTP oom 不在其拦截范围）。
- 前端不改（事件流沿用现有展示）。

## 实施步骤

1. hang_detector：观察模式状态机（正常 → 观察中 → 恢复/判挂死），BMC 活性信号判定，上限终止；时钟与 BMC 探测全部注入。
2. mugen_runner：vm_hang 判定点接入 BMC 门；进入/结论两次抓取取证；事件记录三类。
3. console_capture：补 chassis power status 查询（SEL 查询复用现有实现）。
4. 回退路径：无 BMC 或 VM 不进观察模式，维持现有判定。
5. 文档：新 ADR（含不采用纯放宽阈值、用例感知方案的理由）；Spec 0003 挂死判定语义同步。

## 验证标准

- 新行为均有先失败后通过的测试：观察模式状态机（恢复 / 上限终止 / BMC 报重启）、BMC 查询失败兜底、无 BMC 回退、事件与取证落盘时点。
- ipmitool 与时钟全部注入伪造，测试不依赖真实 BMC。
- 定向测试通过后 `./scripts/check.sh` 通过。
