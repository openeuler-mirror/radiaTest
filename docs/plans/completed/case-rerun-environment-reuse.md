<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: RunJob 用例在来源环境中重跑

## 状态

已完成。

关联决策：[ADR 0028](../../adr/0028-rerun-cases-in-source-environment.md)。

## 目标

允许已登录用户从重跑链最新终态 RunJob 中选择可执行用例，在其来源 VM 或物理机环境中再次执行。
默认选择失败用例；新执行保留独立结果、日志和完整来源关系。

## 范围

- 模块模板和 Test Job 快照增加 `rerun_env_script`；Docker 使用最小重启脚本。
- 重跑按来源 Case Run 所在 EnvSet 分组，复制节点引用并跳过 VM/PXE、Mugen 部署和完整 pre-env。
- 支持 `passed`、`failed`、`error`、`timeout`，并保留每个 Case Run 的直接来源和根来源。
- 后端校验最新链、终态、资源可用性、租约和同环境并发；状态变化返回冲突，不创建半成品执行。
- 每批日志使用独立路径，远端所选 case 的旧输出先归档，源 artifact 不可变。
- 总览按根 Case Run 取最新结果；RunJob 详情按批次展示。
- 重跑候选始终覆盖根 RunJob 用例全集，状态取每个根 Case Run 的链上最新事实；本批结果与候选
  使用独立字段。
- 跨历史批次选择时按根 EnvSet 合并，同一实际环境每批只执行一次 rerun/post hook。
- 前端提供双栏大量用例选择器、状态/环境筛选和紧凑执行历史栏，提交后进入新 RunJob。
- 共享环境按 resource 去重销毁并同步链内节点状态。

## 非目标

- 不自动重跑，不新增轮询频率、后台调度器、通知或外部依赖。
- 不在来源环境不可用时创建替代环境，也不自动续期租约。
- 不允许从历史 RunJob 分叉重跑，不允许同一环境并发重跑。
- 不改变普通 Test Job 的创建 UI 或首次执行流程。
- 不覆盖源 RunJob、Test Job、Case Run 或已经收集的日志。

## 实施与验证

- [x] 增加模型、迁移、Schema、脚本快照和 Docker seed 数据。
- [x] 按来源 EnvSet/Node 构建重跑 Test Job，并实现资源与并发校验。
- [x] 增加复用执行支路、rerun hook、Case Run 溯源、远端输出归档和日志路径隔离。
- [x] 按 resource 去重销毁共享环境，并完善最新结果聚合。
- [x] 实现用例选择器、环境可用性提示、提交导航和执行历史栏。
- [x] 覆盖后端服务、执行器、API、迁移及前端交互测试。
- [x] 运行受影响测试和本地 `./scripts/check.sh`。
- [ ] 在远程 Linux dev 环境验证 VM、物理机和 Docker（本次未执行：开发工作站不运行远程环境联调）。
- [x] 覆盖“首次全量、后续部分重跑、再次仍可选择全量”的链式候选回归。
- [x] 验证跨历史批次混选时的最新事实溯源和根 EnvSet 合并。
