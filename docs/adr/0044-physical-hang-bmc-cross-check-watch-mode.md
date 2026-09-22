<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0044: 物理机挂死判定的 BMC 交叉确认与观察模式

日期：2026-09-10
状态：已接受（2026-09-10 修订：判死信号收缩为机箱电源状态，SEL 不参与判定）

## 背景

2026-09-10 kimariyb 两个 kernel 物理机任务（x86_64，oe_test_ltp）在 LTP `oom01/oom02` 全局 OOM 风暴期间被误判 vm_hang。机器侧证据链：BMC SEL 无重启记录、journald 单 boot 连续（持久化已由 pre_env 启用）、SSH 在风暴结束后自愈、控制节点随后成功 SFTP 回收 LTP 结果。机制：oom0x 用例故意打满内存（实测单进程 158–358GB anon 分配），全局 OOM 与回收风暴期间 SSH 控制面分钟级不可达；检测器按"连续 5×30s 失败 + 复核一次"（ADR 0042）判整机挂死并杀任务。

历史对齐：vm_hang 事件跟随 `oe_test_ltp`、`oe_test_socket_sssd-nss` 两类用例进入 kernel 测试范围出现（kimariyb 8/29、prod 9/5 起），此前从未发生；prod 9/9 事件（172.168.131.196，失联约 150s 压线）与本次同类——SSH 层失联被当成整机挂死。

本质：检测器观测的是"控制面可达性"，产品语义是"整机不可用"。测试机内存被打满时两者解耦：OS 层尚在挣扎、用例仍在推进，控制面却失联。用例是套件认可的测试内容，误杀的代价（整个 pipeline error、后续用例全部损失）远大于继续观察。

## 现场验证与修订（job 10232）

原版决策以"SEL 无用例开始后重启/断电事件"为存活判据，部署 kimariyb 后首次真实遭遇即翻车（job 10232，.71，`ltp/oe_test_ltp`）：

- 机器地面真相：journald 单一 boot、uptime 连续无中断、mugen/LTP 进程全程存活——机器从未重启；SSH 失联约 15 分钟是 `cgroup_fj_stress freezer` 进程风暴压死控制面后自愈。
- .71 的 BMC RTC 狂奔且偏差随运行递增（装机阶段约 +26 分钟 → 判定窗口约 +4.5 小时 → 当日 +7 小时 47 分）：PXE 装机与换内核的三次重启被渲染到 case start 之后，SEL 判"用例开始后重启过"，确认门首查即判死。**即使机器全程健康，这台机器上也必然误判**（换内核重启距 case start 仅约 3 分钟，BMC 时钟快 3 分钟即中招）。
- 同一观测窗口内 BMC 还写入了 3 条虚构 `System Boot Initiated` 事件，chassis 报 `Main Power Fault: true`——SEL 事件内容本身不可信。
- 全程唯一未说谎的带外信号是机箱电源状态（System Power 始终 on）。

结论：SEL 时间戳与服务器时钟不可比（BMC 无 NTP、会漂移甚至狂奔），SEL 事件内容可虚构，且恰恰在最需要保护的压测窒息场景下最不可信。SEL 不能参与判死，只能作取证参考。

## 决策

在 ADR 0042 的"阈值+复核"之后加一道**带外电源确认门**，仅对配置了 BMC 的物理机生效：

1. **电源判据（三态）**：`chassis power status` 为 on → True；off → False；查询失败/超时/输出歧义 → None（不下结论）。复用取证通道，密码经 stdin 传入不入 argv。SEL 不参与判定，仅随取证产物原样采集。
2. **观察模式**：阈值+复核失败后，三态均进观察模式——心跳照常 30s，电源复查降频每 3 分钟一轮；SSH 恢复 → `hang_recovered` info 事件，用例继续执行。
3. **断电宽限**：观察期内任何时刻（含阈值首查）读到电源 off → 从首次 off 起锚定 10 分钟（`WATCH_POWER_OFF_DEADLINE_SECONDS=600`）；宽限内 SSH 恢复 → 继续执行；到点未恢复 → 判死，detail 注明电源证据。宽限锚定后取代观察上限（判死时刻可晚于 30 分钟）。10 分钟定值依据：正常重启 10 分钟内必然回来（实测 .71 暖重启到 SSH 恢复约 5 分钟）；大内存机器冷上电 POST 可能超出，属标定风险，常量可调。
4. **观察上限**：全程电源 on 或查询失败（窒息类）→ 观察满 30 分钟（代码常量）兜底判死。判死语义与现有 vm_hang 完全兼容，错误详情注明判死依据。
5. **事件与取证**：进入观察（`hang_watch`，warning，注明电源开启/断开/查询失败）与出结论（恢复/判死）各留事件一次，并各抓一次 BMC 取证落盘（`bmc-<suite>-<case>-watch-entry.log` / `-watch-recovered.log`）；观察中首次读到 off 追加一条 `hang_watch` 事件；判死时沿用原取证命名。
6. **适用范围**：VM、无 BMC 物理机、凭据解密失败一律跳过确认门，维持原判定。观察期间取消/软超时语义不变。

## 备选方案与不采用理由

- **纯放宽阈值（如 10×30s）**：实测 SSH 失联窗口最长约 17–20 分钟（job 10230），要么救不回、要么把真挂死发现拖到同样量级。带外证据与 OS 内存压力解耦，是区分真挂死与假失联的正交信号。
- **用例感知容忍（识别 LTP oom 类用例放宽心跳）**：把判定逻辑耦合进用例知识，stress-ng 等其他内存压力来源覆盖不到，名单还需随套件维护。BMC 门不依赖任何用例信息。
- **SEL 时间戳容差（since 前移/加宽限）**：治标不治本——10232 的偏差是小时级且递增，任何容差都覆盖不了，且事件内容本身会虚构。
- **SEL 条目 ID 基线（case start 记录条目集，确认时只看新增）**：能治时钟漂移，治不了 BMC 虚构事件（10232 的 3 条假 boot 事件就写在观测窗口内），在坏 BMC 机器上同样误判。
- **BMC 查询失败即判死（保守回退）**：BMC 单独抖动（固件重启、繁忙，实测出现过 30s 超时）会直接退回误杀路径。观察模式 + 上限兜底既给 BMC 恢复机会，又保证任务不悬挂。
- **无限观察**：真挂死 + BMC 故障的组合会永久悬挂任务，必须有上限。
- **用例过滤（同 ADR 0043）**：LTP oom 用例是合法测试内容，不伪造系统状态、不杀机器，过滤会损失覆盖；ADR 0043 拦的是"会把机器打下去"的用例，与本门互补不互替。

## 范围取舍

- `oe_test_socket_sssd-nss` 类失联（kimariyb 8/31–9/1、prod 9/5–9/8 的另一高频来源）机制未取证，本次不查不修；若其本质同为"机器活着、控制面失联"，本门会顺带缓解，但不做此假设。（后续：已由 [ADR 0046](0046-vm-outofband-hang-recovery.md) 取证为 NSS 阻塞自愈，VM 侧带外判活与宿主机硬复位恢复见该 ADR。）
- 不改心跳间隔/阈值参数；不做自动断电恢复（沿用 ADR 0042：物理机生命周期归调用方）。
- 首查电源 off 不立即判死（对原版规则的语义变更）：单次 BMC 读数不可全信，且死机晚 10 分钟出结论无实质损失——job 已注定失败，仅收敛方式不同。
- 前端不改：`hang_watch`/`hang_recovered` 事件走现有事件流展示。
- .71 机器自身的硬件问题（BMC RTC 狂奔、Main Power Fault、OS 时钟 +3.9 天）属运维事项，不在本 ADR 范围。

## 影响

- `HangDetector` 状态机扩展为：正常 → 观察中 → 恢复/判死；新增 `confirm_fn`（三态电源）、`on_watch_start`/`on_recovered` 回调与断电宽限锚定（恢复时清除锚定与判死标记），原"阈值+复核"语义不变。
- 观察期间 case 的 SSH 长命令继续阻塞主线程，依赖心跳恢复或判死后经 `cancel_event` 中断——与现有挂死路径一致，不新增并发路径；检测器线程内的观察事件/取证走独立数据库会话。
- 事件流新增 `hang_watch`/`hang_recovered` 两个 phase，产物新增 watch-entry/watch-recovered 命名。
- 误判代价的有意变化：真挂死且表现为"电源 on 无断电"（如 panic 后卡死不重启）或 BMC 同时故障时，判死最迟 30 分钟（原约 3 分钟）；电源断开场景最迟为首次 off 后 10 分钟。
- **ipmitool 环境约束**：子进程环境钉死 `LC_ALL=C`、`TZ=UTC`——ipmitool 输出格式与 SEL 时间戳渲染随 locale/时区变化，钉死环境保证电源状态判定与 SEL 取证产物的输出确定性（不可破坏的约束）。
