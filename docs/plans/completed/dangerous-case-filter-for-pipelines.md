<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# 危险用例过滤(流水线链路)

## 状态

已完成：实现（`cd2f69f feat(pipeline): 危险用例过滤`）、迁移 `20260909_0043_mugen_cases_dangerous_flags`、ADR 0043 与 Spec 0003 §8.1 同步、`docs/feat/dangerous-case-filter/` 特性档案均已交付；运维收尾按计划内标注不在本计划范围、单独执行。

## 背景与问题

2026-09-08 prod 14 个 VM 流水线任务异常:mugen 用例索引同步到 `65bedba5` 后,systemd suite 首次进入用例集,其中 `oe_test_service_initrd-cleanup` 等用例的脚本故意 `touch /etc/initrd-release` 绕过 systemd 的 ConditionPathExists 保护,强行启动会 isolate 到 switch-root 的单元,导致 VM 永久挂死。队列中还有 26 个关机类用例(`systemd-reboot`、`target_runlevel0` 等)尚未执行即被熔断批量标 error。这类"把机器打下去"的用例不能进入由 SSH 驱动、带 post_env 收尾的长流水线。

## 范围

- 新增危险用例识别模块(test_management 下,公共可复用),三道判据命中任一即判危险:
  1. 名字规则:单元段 `initrd` 前缀 + 精确危险单元集合(reboot/poweroff/halt/kexec/shutdown/suspend/hibernate/suspend-then-hibernate/hybrid-sleep/soft-reboot/exit/systemd-exit/telinit/ctrl-alt-del/runlevel0-6 等)
  2. 高精度脚本扫描:同步 mugen 仓库时扫描用例脚本,命中 `touch /etc/initrd-release`(或重定向写该文件)、显式 `systemctl isolate/switch-root/kexec/halt/poweroff/reboot` 即打标
  3. 内置兜底名单(代码常量,精确用例名)
- `mugen_cases` 表新增 `dangerous`、`dangerous_reason` 两列,同步时计算并全量重建
- 流水线 builder(`build_test_job_for_run_job`)在用例解析后过滤危险用例:被拦用例不生成 TestCaseRun(不进清单),并在 TestJob 执行事件中留痕( phase=`cases_filtered`,message 含跳过数量与用例名单)
- 同步任务读 suite2cases 时同时读 suite `path` 指向的用例脚本内容,传入 sync service

## 明确不做

- 手工测试任务链路不过滤(识别模块保持公共,后续接入是加法)
- 不建管理端名单维护界面/表,名单走代码内置 + 发版
- 不做宽匹配扫描(宁可漏网由名单兜底,不做静默误伤)
- 不做 VM 失联自动重建、post_env 重试等韧性增强
- 不回退 mugen 索引版本
- rerun 链路不加过滤:被拦用例不会产生执行记录,天然无 rerun 资格

## 实施步骤(TDD,每步先失败测试再实现)

1. `dangerous_cases.py` 识别模块:名字规则 + 内置名单 + 脚本内容扫描(纯函数,单测覆盖命中/不命中/边界如 `pcp-reboot-init` 不误伤)
2. `mugen_cases` 模型加列 + alembic 迁移(仅 DDL,前进式)
3. 同步任务扫描脚本 + `sync_mugen_cases` 写入标记(单测:仓库 fixture 含危险脚本时索引行带标记;含无辜 "reboot" 字样的脚本不打标)
4. builder 过滤 + `record_test_job_event` 留痕(单测:含危险用例的清单被拦、事件写入、正常用例不受影响)
5. `./scripts/check.sh`

## 验证标准

- 上述单测先失败后通过;`./scripts/check.sh` 通过
- kimariyb 环境实测:触发含 `oe_test_service_initrd-cleanup` 的流水线任务,确认用例不进入执行清单、事件留痕可见、任务不再因该用例异常
- 文档同步:Spec(0003 用例清单构造与留痕行为)+ ADR(内置名单与高精度口径、只拦流水线的取舍)

## 运维收尾(不在本计划内,单独执行)

- 人工清理 14 台挂死 VM;prod 部署本修复后 rerun 当天 14 个失败 RunJob 验证
