<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# 物理机挂死判定改为电源状态单一信号（ADR 0044 修订）

## 背景与动机

job 10232（.71，`ltp/oe_test_ltp`）实证 ADR 0044 的 SEL 判据在真实环境不可靠：

- .71 的 BMC RTC 狂奔（偏差随运行递增：装机阶段约 +26 分钟，判定窗口约 +4.5 小时，当日 +7 小时 47 分），PXE 装机与换内核的三次重启被渲染到 case start（09:13:25 UTC）之后，SEL 判"用例开始后重启过"，BMC 门首查即判死。
- 机器地面真相：journal 单一 boot、uptime 连续无中断、mugen/LTP 进程全程存活——机器从未重启；SSH 失联是 `cgroup_fj_stress freezer` 进程风暴压死控制面，约 15 分钟自愈（负载 5.69 → 0.00）。
- 同一观测窗口内 BMC 还写入了 3 条虚构 `System Boot Initiated` 事件，且 chassis 报 `Main Power Fault: true`——这台 BMC 的事件流本身不可信。
- 全程唯一未说谎的带外信号是机箱电源状态（System Power 始终 on）。

用户确认的新规则：正常重启 10 分钟内必然回来；电源断开场景给 10 分钟宽限，其余场景应多等待（观察上限维持 30 分钟）。

## 范围

- 判死信号收缩：BMC 带外判据只看机箱电源状态（`chassis power status`）；SEL 不再参与判定，仍随取证产物原样采集（watch-entry / recovered / 判死诊断，不变）。
- 断电宽限：观察期内任何时刻（含阈值首查）读到电源 off → 从首次 off 起锚定 10 分钟（`WATCH_POWER_OFF_DEADLINE_SECONDS=600`）宽限；宽限内 SSH 恢复 → `hang_recovered` 继续执行；到点未恢复 → 判死，detail 注明电源证据（`bmc_declared=True`）。
- 首查 off 不再立即判死，统一进入观察模式（对 ADR 0044 原规则"False 即判死"的语义变更，理由见 ADR 修订记录：单次 BMC 读数不可全信，且死机晚 10 分钟出结论无实质损失）。
- off 锚定后断电宽限取代观察上限（判死时刻可晚于 30 分钟）；全程电源 on（或查询失败）则维持 30 分钟上限兜底。
- SSH 恢复时清除 off 锚定与上一 episode 的 `bmc_declared` 标记，避免污染后续 episode。
- 事件文案：watch-entry 消息区分"电源开启/电源断开/查询失败"三态；观察中首次读到 off 追加一条 `hang_watch` 事件（每个 case 一次）。
- 删除 `sel_has_disruptive_event` 与 `_REBOOT_EVENT_KEYWORDS`（无其他调用方）；`bmc_machine_alive` 更名为 `bmc_power_on`（签名去掉 `since`）。

## 明确不做

- 不做 SEL 时间戳容差或条目 ID 基线比对——事件本身会虚构，修补不可信信号没有意义。
- 不做冷上电 POST 时长自适应：10 分钟为经用户确认的定值；大内存机器冷上电 POST 可能超出，标定风险记入 ADR，常量可调。
- 不新增轮询、定时器、后台任务、表字段或新依赖；BMC 复查复用观察模式既有节奏。
- 不处理 .71 机器本身的硬件问题（BMC RTC 漂移、Main Power Fault、OS 时钟 +3.9 天，建议报修，人工处理）。
- prod 部署不在本计划内（部署需另行授权）。

## 实施步骤

1. 测试先行（先失败）：
   - `test_console_capture.py`：`bmc_power_on` 三态（on/off/查询失败/歧义输出），以及"电源 on + SEL 查询失败 → 仍 True"的 SEL 不参与回归锁。
   - `test_hang_detector.py`：首查 off 进观察并锚定宽限；宽限到点判死；宽限内 SSH 恢复得救；off 锚定取代 30 分钟上限；恢复后锚定与标记复位；既有 cap/unknown/recovered 用例语义保持。
   - `test_pipeline_execution.py`：判死 detail 含"电源断开"证据；watch-entry 事件文案含电源状态；既有 watch/timeout 用例适配。
2. 最小实现：`console_capture.py` 电源单信号；`hang_detector.py` 断电宽限状态机；`mugen_runner.py` 门构造与文案。
3. 文档：修订 ADR 0044（现场证据、规则变更、不采用方案），同步 Spec 0003 §4.6；完成后本计划移入 `completed/`。

## 验证标准

- 新增/修改的关键行为测试先失败后通过；`./scripts/check.sh` 通过。
- .71 场景回放锁定：电源 on + SEL 虚构重启事件 → 不判死（SEL 不参与判定）。
- 电源 off → 10 分钟宽限内未恢复 → 判死且 detail 注明电源证据；宽限内恢复 → `hang_recovered` 继续执行。
- 审查通过后准备 merge commit message，经授权合入 main。
