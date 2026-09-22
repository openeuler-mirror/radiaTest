<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0042：物理机挂死误判治理（复核确认）与 BMC 取证

日期: 2026-09-09

## 状态

已采纳（Grill 确认，范围与验证标准见 `docs/plans/completed/physical-hang-misjudgment-and-forensics.md`）。

## 背景

prod 多个 kernel 流水线任务被判 `vm_hang`（"VM/物理机挂死（心跳连续失败）"），全周无
一次 LTP 用例正常收尾，且每次都无法定界。对 2026-09-09 任务 10134
（172.168.131.196 / openEuler 24.03-LTS-SP3）的取证给出实锤：

1. **判死节奏反推**：case 开始 151 秒即判挂死，恰好等于 5 次 30s 间隔的秒级快速失败
   （每次 SSH 在 1s 内被拒/重置）。真整机失联（SYN 无响应）时每次失败吃满 30s 超时，
   判定最早也要约 300s，与观测不符。
2. **BMC SEL 证据**：挂死窗口（02:43–02:45 UTC）BMC 无任何 System Restart/断电记录，
   排除整机重启；"秒拒"特征进一步排除 panic 死机（panic 后 SYN 被静默丢弃只会慢超时）。
   9/5、9/8 两次 vm_hang 的 BMC 亦无重启记录。
3. **恢复在判定落锤的同一秒**：判死后 0.27s 的 post_env SSH 立即成功。故障持续约
   150s，与判定阈值（5 × 30s）压线——ADR 0016 的自愈机制差约 1 秒即可救回本次任务。
4. **取证真空**：物理机挂死路径的 console 抓取一直延后（`_capture_and_store_console`
   对无宿主资源直接 return），journald 为易失存储且 PXE 重装清盘，每次事件后查无实据。

结论：这些事件多数不是"物理机挂死"，而是 SSH 服务层的瞬态不可达（可能与 LTP 用例
启动阶段的 dnf/git clone 负载相关，OS 层根因待下次留证后定界），但它们被一票否决成
"整机挂死"，触发熔断并作废整个多日流水线。

## 决策

### 1. 判死前复核一次

`HangDetector` 连续失败达 `max_failures` 后不再立即 fire `on_hung`，先等待一个
interval 复核一次：复核成功 → 失败计数清零、用例继续执行；复核仍失败 → 判死。
真挂死的杀掉延迟从约 300s 增至约 360s（超时型失败每次吃满超时），相对多日任务
可忽略。判死语义（只中断当前 case、连续 3 次熔断跳过剩余 case）不变。

### 2. 心跳失败模式进错误详情

心跳探活失败按传输特征分类计数：失联（连接阶段即超时/无路由——SSH 内层
`ConnectTimeout=10` 先于进程超时生效，整机失联表现为 exit 255 +
"Connection timed out"，整机失联嫌疑最大）、超时（进程级 30s 超时，TCP 已建立、
echo 卡死，OS 活着但重度受阻）、拒绝（Connection refused）、断连
（Connection reset/closed/banner exchange）、其他。判挂死时把摘要拼进
`mark_case_execution_error` 的 detail，自动流入 case_error 事件与任务错误信息。
拒绝/断连/超时型说明 OS 与网络层仍存活（sshd 层或负载问题）。该信息只服务人工
定界，不参与自动判定。单次失败仍只记 debug 日志，不发事件。

### 3. 物理机挂死经 BMC 取证（落地 ADR 0032 延后项）

`_capture_and_store_console` 的物理机分支改走 BMC：`ipmitool sel list` /
`chassis status` / `sdr elist`，存 `bmc_diagnostic` artifact（与 VM 的
`console_diagnostic` 并列）。凭据取自 `physical_spec` 的应用层加密密文。
BMC 独立于被测 OS，整机挂死仍可读 SEL，是区分"真重启断电"与"SSH 层抖动"
的决定性证据（本次调查即依赖它）。

### 4. kernel 模块启用 journald 持久化

`KERNEL_PRE_ENV` 创建 `/var/log/journal` 并重启 journald。PXE 基础镜像的 journal
为易失存储，机器侧证据（panic/OOM/sshd 日志）随重启丢失；pre_env 在换内核重启之后
执行，持久化恰好覆盖用例执行期（含 LTP 中途触发 reboot）。机器侧证据按设计只保留
到下一次 PXE 重装，跨任务的长期取证依赖 BMC SEL。

## 取舍 / 不采用

- **不采用挂死后自动断电重启/自动重试 case**：物理机生命周期归调用方（cancel 语义
  同款约束）；对被测机自动断电可能毁掉现场、与调用方操作冲突。平台只负责把
  "真挂死"与"抖动"区分开并留证，恢复交给人工或调用方。
- **不采用调大 max_failures 替代复核**：调参与复核对压线场景的容忍窗口数学上近似
  （150s→180s），但复核是不可逆动作前的确认语义，保持"5 次连续失败"既有文档与
  心跳节奏不变；将来做失败模式分级判定时，复核点是现成挂钩位置。
- **不采用失败模式分级判定**（拒绝型放宽、超时型从严）：SSH 错误文本语义不完全
  可靠且无历史数据支撑参数；先记录模式积累数据，判定规则留待有据再议。
- **不采用单次心跳失败即发 task_event**：长任务叠加网络抖动会刷屏；自愈型瞬断的
  事后可见性由 bmc_diagnostic 与持久 journal 覆盖。
- **不把 journald 持久化烘进 PXE 基础镜像**：镜像构建在仓库之外；pre_env 三行即可
  达成，且不扩大影响面（仅 kernel 模块）。

## 影响

- 后端：`test_management/hang_detector.py`（复核确认）、
  `test_management/frameworks/mugen_runner.py`（`_HeartbeatStats`、detail 拼接、
  `_capture_and_store_bmc_diagnostics`）、`test_management/console_capture.py`
  （`capture_bmc_diagnostics`）、`pipelines/seed.py`（KERNEL_PRE_ENV）。
- Spec 同步：`docs/spec/0003-test-pipeline.md` §4.6、§4.8、kernel 模块模板描述。
- 前端无改动：artifact 类型展示为通用列表，无 `console_diagnostic` 硬过滤（已查证）。
- 已知边界：SSH 瞬断若超过复核窗口（约 180s）仍会判死；此类长瞬断与真挂死在
  当前证据下无法区分，留待 bmc_diagnostic/journal 数据积累后重估。
