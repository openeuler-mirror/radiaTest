<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0023：pkgcmd/pkgserver 的 physical env_set 复用 kernel 物理机（隐式锁 + 前序链查找 + fallback）

日期: 2026-08-04

## 状态

已采纳。整个测试期以 `management_status=maintenance` 充当隐式锁的部分已被 [ADR 0029](0029-physical-test-resource-usage-state.md) 取代；前序模块环境复用仍是独立、尚未实施的范围。

## 背景

update 流水线中 kernel、pkgcmd、pkgserver 三个模块都涉及物理机执行。当前每模块各自占一台 `usage_scenario=<module>-update` 物理机，PXE 重装成 pipeline OS 后跑测试（`physical.py:73 create_env_node_physical`）。但物理机资源有限——最好情况物理机数恰好覆盖 kernel 模块（每版本一台），pkgcmd/pkgserver 没有独立物理机；且 pkgcmd/pkgserver 的 physical 测试执行时间短，PXE 重装（~30min）的相对成本高。

用户诉求：pkgcmd/pkgserver 的 physical env_set 借用 kernel 已装好的物理机跑，省掉各自 PXE 重装。但版本数动态变化（物理机够→kernel 各版本并行；不够→kernel 多版本排队复用同台机器），平台须同时支持两场景。

约束：both 模块在 ADR 0018 已定为 1 RunJob + 内部 vm/physical 两 env_set 并行（ThreadPoolExecutor）。引入 RunJob 间显式 Celery 依赖链会逼 both 拆回 2 RunJob 才能做 env_set 级依赖，推翻 ADR 0018，不可接受。

## 决策

### 1. 前序链查找（不引入显式 Celery 依赖）

pkgcmd/pkgserver 的 physical EnvSet 在 `create_env_node_physical` 内按“前序链”查同 `(execution, version, arch)` 的就近在场前序模块 RunJob；前序 TestJob 终态后，若其物理 Env Node 关联的资源仍可用，则复用该机器（不重装）。查不到可复用机器则 fallback 自重装。不引入 RunJob 间 Celery 依赖。

不采用：显式 Celery 依赖链（kernel→pkgcmd→pkgserver 任务链）——会逼 both 模块拆回 2 RunJob 才能做 env_set 级依赖，推翻 ADR 0018。

### 2. 前序链：就近上游

- pkgcmd 前序链：[kernel]
- pkgserver 前序链：[pkgcmd, kernel]（pkgcmd 不在场则回退 kernel）

docker/pkgmanage 纯 vm，不参与复用链。

不采用：严格固定前序（pkgserver 固定等 pkgcmd）——"勾 kernel+pkgserver 无 pkgcmd"组合下会浪费 kernel 机器去自重装 pkgserver-update。

### 3. 复用条件看机器可用性，不看前序测试成败

复用条件 = 前序 TestJob 已终态、前序 physical Env Node 已关联资源、资源 `management_status=active` 且 SSH 可达。kernel LTP failed 但机器装好 → pkgcmd 照常复用。

不采用：看 kernel RunJob succeeded 才复用——kernel 任何一个 LTP 用例失败就连锁搞挂 pkgcmd/pkgserver physical，放大失败面，违背"借机器不是借测试结果"。

### 4. fallback 统一：查不到可复用机器就自重装

fallback 触发条件统一：前序不在本次触发列表 / 前序在场但机器不可用（PXE 失败 / 超时被软杀 / SSH 不通）都 fallback 到按 `<module>-update` 选取测试空闲资源并 PXE 重装（当前行为）。fallback 机器也找不到 → error。

不采用：前序在场但机器不可用直接 error 不 fallback——违背 pkgcmd physical"能跑就跑"的目标。

### 5. 资源排他以执行事实为准

候选认领遵循 ADR 0029：worker 以数据库行锁检查有效租约、`active`、arch、`usage_scenario` 和无活动物理 Env Node，并立即写入新 Env Node 的 `resource_id`。持久化关联让资源在新 TestJob 终态前保持 `test_status=testing`，阻止并发重认领。

`management_status=maintenance` 只覆盖实际 PXE 重装的原子阶段；完成后恢复 `active`。复用路径不通过 cleanup 将测试期锁改回 `active`，因为测试期没有此类锁。

### 6. 等待与场景兼容

资源不足时，等待受当前 TestJob 的既有总截止时间约束。实现不得采用固定 sleep-and-retry、单独的资源锁表、全局并发提升或按模块拉长 `soft_time_limit`。前序测试完成后，派生的 `test_status` 消失，后续 worker 以同一认领规则继续；不需要显式 Celery 依赖。

### 8. mugen 重建不省

复用机器时 `prepare_mugen` 仍 `rm -rf /opt/mugen` + 重建。复用只省 PXE 重装（~30min），不省 mugen 部署（几分钟），保证环境干净避免 kernel LTP 拽留影响 pkgcmd。

### 9. keep_env 语义变化（接受）

kernel 跑完机器被 pkgcmd/pkgserver 复用，pre_env 装包改 OS 状态。kernel 测试结果（日志 / ltp_results）已收集不受影响；人工检查机器时看到末模块跑完状态。接受——keep_env 目的是防过早销毁，不保环境纯净。

### 10. 实施前需重新收敛

复用目标尚未实施。开始编码前必须基于 ADR 0029 重新 Grill，明确前序终态判断、候选查询与行锁顺序、等待超时传播和 fallback；不得恢复已取代的 `physical-machine-scheduling` 计划。

## 影响

- `backend/app/modules/test_management/envs/physical.py`：若未来实施，`create_env_node_physical` 增加前序候选查询，并复用 ADR 0029 的行锁和活动节点排他规则。
- 不要求 `cleanup_env_physical`、`_run_env_set_thread` 或 `soft_time_limit` 为测试期状态锁新增行为。
- [物理机复用历史提案](../plans/superseded/physical-machine-reuse.md) 保存已取代的前提；重新 Grill 后另建可执行实施计划，并同步 Spec 0003 与 CONTEXT。
