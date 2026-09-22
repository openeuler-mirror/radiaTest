<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0028：在来源环境中按选重跑 RunJob 用例

## 状态

已接受(Accepted)。

## 决策

- 已登录用户只能从重跑链上最新的终态 RunJob 发起用例重跑；默认选择失败用例，也可选择
  `passed`、`error` 或 `timeout` 的可执行 Mugen Case Run。
- 每次打开重跑选择器都以根 RunJob 的用例集合为候选全集，并按根 Case Run 取链上最新执行事实。
  当前 RunJob 的 `case_runs` 仍只表示本批次，独立的 `rerun_candidates` 承载重跑候选。
- 每次重跑创建新的 RunJob、Test Job、EnvSet、Node 和 Case Run。新记录保存直接来源与根来源，
  源执行事实和已收集日志不可变。
- 新 EnvSet 按所选 Case Run 的根 EnvSet 分组；Node 复用根来源节点的 resource，不申请 VM、
  不执行物理机 PXE、不重新部署 Mugen，也不执行完整 `pre_env_script`。
- 模块模板增加 `rerun_env_script`。Test Job 创建时保存脚本快照；每个复用 EnvSet 在执行所选
  case 前运行一次，之后继续运行来源快照中的 `post_env_script` 以整理结果。
- Docker 模块的重跑脚本仅重启既有 `openEuler_test` 容器并等待其恢复运行；不重启 Docker
  daemon，也不重新安装 Docker、拉取镜像或重建容器。其他模块默认使用空脚本。
- 同一根重跑链的资源不能并发执行多个重跑，也不能在重跑活动期间销毁。来源资源已释放、租约
  过期、节点不可达或环境正在使用时拒绝请求，不回退到新建环境。
- 每个 Case Run 保存直接来源和根来源；再次重跑时直接来源指向该根用例的最新 Case Run。总览和
  重跑候选按根 Case Run 读取链上最新结果；RunJob 详情按执行批次独立展示结果和日志。
- 日志 artifact 使用 RunJob/Test Job 独立路径。重跑前归档所选 case 的远端旧输出，新执行只
  收集本批次输出，不覆盖已收集 artifact。
- 共享环境销毁按根重跑链解析并按 resource 去重；实际资源只销毁一次，链内引用同步收敛为已销毁。

## 取舍

复用节点能保留失败现场并减少完整环境准备，但意味着环境是否仍可用成为重跑前置条件。因此不做
“不可用时新建环境”的隐式降级，也禁止共享环境上的并发重跑。新增 EnvSet、Node 和 Case Run 仍是
必要的执行事实；resource 复用不表示复用或覆盖源数据库记录。

重跑只复用来源执行已经持久化的脚本和节点快照，不读取模块模板的当前值。这样牺牲了临时修改模板
立即影响旧执行的便利，换取可复现的执行链和明确的审计边界。

本决策取代 [ADR 0027](0027-rerun-selected-pipeline-cases.md) 中“仅失败用例、按名称去重并重新走完整
执行环境”的部分；新 RunJob、新 Test Job、来源链和源事实不可变的原则继续保留。
