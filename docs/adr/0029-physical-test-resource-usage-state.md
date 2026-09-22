<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0029：物理机测试占用由执行事实派生并用于调度

日期: 2026-09-02

## 状态

已接受(Accepted)。

## 决策

- 管理状态、租约状态与测试状态保持独立：`management_status` 继续表达资源是否可管理，
  `occupancy_status` 表达租约关系，Resource API 额外返回派生的 `test_status=idle|testing`。
- `testing` 不保存为 Resource 数据库列。物理 Env Node 已关联资源且所属 Test Job 为非终态时，
  该资源处于测试中；API 同时返回关联的 Test Job ID。
- worker 在 PXE 前以数据库行锁认领一台满足“触发者有效租约、active、arch 与
  usage_scenario 匹配、当前无活动测试”的物理机，并立即持久化 Env Node 关联。竞争者等待该
  执行事实消失，等待上限沿用 Test Job 的 15 小时总截止时间。
- 流水线触发前按唯一 `(arch, usage_scenario)` 检查每组至少一台测试空闲自有机器。多版本不按
  数量预留机器，而是在 worker 中排队复用；任一组无可用机器时整次触发返回冲突。
- 测试中的资源禁止释放租约、修改资源字段和手动 PXE 重装。查看、凭据读取和租约延长不改变
  测试环境，继续允许。

## 取舍

不把整个测试期写成 `management_status=maintenance`。该值属于管理维度，复用它会让用户无法
区分人工维护与正在测试，也会使管理权限和调度锁耦合。PXE 原子操作仍可在实际重装期间使用
`maintenance`，重装完成后恢复 `active`；此时独立的 `test_status` 仍为 `testing`。

不新增 `resources.test_status` 或资源锁表。Env Node 与 Test Job 已经保存了资源被哪个执行使用的
事实，重复保存状态会引入 worker 中断后的陈旧锁。数据库行锁只保护认领瞬间，持久化后的节点关联
负责后续可见性和排他判断。

本决策取代 [ADR 0023](0023-pkgcmd-pkgserver-physical-reuse-kernel-machine.md) 中尚未实施的
“整个测试期用 management_status 充当隐式机器锁”部分。ADR 0023 的前序模块环境复用方案仍属
独立范围，本次不实现。
