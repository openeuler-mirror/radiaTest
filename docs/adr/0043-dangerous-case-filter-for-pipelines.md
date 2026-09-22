<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0043: 流水线危险用例过滤

日期：2026-09-09
状态：已接受

## 背景

2026-09-08 prod 14 个 VM 流水线任务异常。mugen 用例索引同步到新 commit 后，systemd suite 首次进入用例集；`oe_test_service_initrd-cleanup` 等用例的脚本故意 `touch /etc/initrd-release` 绕过 systemd 的 `ConditionPathExists` 保护，强行启动会 isolate 到 switch-root 的单元，导致执行中的 VM 永久挂死。由于流水线是 SSH 驱动的串行长队列（后续用例 + post_env 收尾都依赖 VM 可达），一台 VM 挂死即触发"连续 3 次 SSH 失败"熔断，剩余用例批量标 error、任务整体 error，且留下 14 台挂死 VM 占用资源池。队列中还有 26 个关机类用例（`systemd-reboot`、`target_runlevel0` 等）未执行即被熔断——即使拦掉单个用例，同类地雷仍在。

这类用例在 mugen 语境下本身"能测"（一次性 VM、测完重建即可），但在 radiaTest 流水线语境下不可执行。判别标准不是"用例写错"，而是"用例会把被远程驱动、还有后续工作的机器打下去"。

## 决策

在流水线 builder 生成执行清单前，统一过滤危险用例，判据三道，命中任一即拦：

1. **名字规则**：mugen 用例名对应 systemd 单元名，危险单元是稳定集合——`initrd` 前缀 + 精确单元名单（reboot/poweroff/halt/kexec/shutdown/suspend/hibernate/soft-reboot/exit/telinit/ctrl-alt-del/runlevel0-6 及 systemd- 前缀变体）。整词精确匹配，不做子串（`pcp-reboot-init` 实测无害，不能误伤）。
2. **同步脚本扫描**：同步 mugen 仓库时扫描用例脚本，只匹配高精度模式（伪造 `/etc/initrd-release`、显式 `systemctl isolate/switch-root/kexec/halt/poweroff/reboot`），结果落 `mugen_cases.dangerous`/`dangerous_reason`。
3. **内置兜底名单**：代码常量，预置本次事故元凶；规则覆盖不到的新个例经代码评审追加，走正常发版。

被拦用例不生成 TestCaseRun（不进清单、不进统计），builder 写一条 `cases_filtered` 事件到 TestJob 事件流留痕。

## 备选方案与不采用理由

- **管理端可维护名单（表 + API + 页面）**：危险用例是极低频事件（mugen 多年首例），为此建一套管理界面收益配不上维护成本；内置常量加一条走发版即可。名单若将来高频化，迁移到数据库是纯加法。
- **宽匹配脚本扫描**（出现 reboot/halt 字样即拦）：误伤是静默的——正常用例无声消失、测试覆盖缩水且难发现；漏网是可见失败——任务报错、可定位、补一条名单即可。两种错误代价不对称，取宁漏勿误伤。
- **VM 失联自动重建续跑**：改动状态机与资源语义，复杂度高；"平台链路异常 = error"是既定产品语义，不因个别用例推翻。
- **mugen 索引回退旧 commit**：会丢掉其他正常新增用例，代价不成比例。
- **只修上游 mugen**：治本但周期不可控，且 prod 已暴露；上游修复与本防线互补，不互替。

## 范围取舍

- 只拦流水线 builder 链路；手工测试任务暂不接入。识别逻辑为公共模块，后续接入手工链路是一行调用。
- rerun 链路不过滤：被拦用例不产生执行记录，天然无 rerun 资格；rerun 复用来源记录，不重建清单。

## 影响

- `mugen_cases` 新增 `dangerous`/`dangerous_reason` 列（迁移 20260909_0043，仅 DDL）；名字规则不落库、过滤时动态计算，规则演进不需要重新同步。
- 被拦用例的审计依据在 TestJob 事件流（`cases_filtered`），用例统计"总计"变小是预期行为。
- 上游 mugen 修复（initrd 用例自查环境）仍值得推动，与本防线互补。
