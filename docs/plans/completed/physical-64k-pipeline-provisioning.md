<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Plan: 修复物理机 64k 流水线环境准备

## 状态

已完成实现与定向验证。

## 范围

- 手动物理机 PXE 保持只安装基础镜像，不增加 64k 选项或 API 字段。
- 仅支持代码明确列出的 `openEuler-24.03-LTS-SP4-64k` 与 aarch64 组合；流水线触发、
  VM 申请及 worker 分层校验。
- 物理流水线把 Test Job 的 64k 目标版本传给 PXE 后处理，基础 PXE 完成后安装最新轮
  `kernel-64k`、设置默认启动项、重启并验证页大小，全部成功后节点才 `ready`。
- 普通 VM 申请保留最多 5 轮回退；VM 与物理 update 流水线只检查最新轮。
- 最新轮未转测 64k 时，仅将当前 Node、EnvSet 和 Case 收敛为 `not_executed`，Test Job
  正常成功；安装或启动故障则物理节点 `error`、资源 `disabled`，VM 回滚。
- 成功后资源记录规范化 64k OS 版本和 `uname -r` 的真实内核版本。

## 非目标

- 不给手动物理机重装增加 64k 选项。
- 不新增数据库字段、安装镜像记录、后台任务、依赖或远程 repo 页面探测。
- 不自动支持未列入代码规则的后续 64k 版本。

## 实施步骤

1. 添加目标版本传递、唯一支持版本、最新轮未转测及页大小验证的失败测试。
2. 扩展现有 64k 安装核心，统一 VM/物理机的默认内核切换、重启等待和验证。
3. 用结构化结果收敛当前 EnvSet，删除依赖全局 TaskEvent 文本的跳过判断。
4. 同步 ADR 0024、资源管理 Spec、流水线 Spec 与前端 API 状态类型。
5. 运行定向测试、静态检查并复核最终 diff。

## 验证标准

- 物理流水线使用基础 SP4 PXE 镜像，但 Step 6 收到保留 `-64k` 的目标版本。
- `kernel-64k` 成功安装、设为默认、SSH 恢复且页大小为 65536 后才出现
  `physical_node_ready`。
- 最新轮没有 64k 时不查询旧轮，当前 Node、EnvSet、Case 为 `not_executed`，物理机
  active 且仍归原用户占用。
- 安装、默认启动项、SSH 或页大小验证失败时节点不 ready，物理机 disabled；普通 VM 回滚。
- SP4 以外的 64k 版本和非流水线计划内的架构在创建任务前被后端拒绝；update 流水线
  继续按既有规则跳过 x86_64/-64k 组合。

## 验证结果

- 物理环境定向测试、64k 安装与校验测试、流水线未执行状态测试、手动 PXE 兼容测试通过。
- Ruff、Python 编译检查、前端格式检查与 TypeScript 类型检查通过。
- 项目全量检查执行到后端测试；受仓库既有 macOS shell、缺少 `sshpass` 和旧 4k 内核测试桩
  问题阻断。与本计划相关的失败测试桩已修正并单独回归通过。
