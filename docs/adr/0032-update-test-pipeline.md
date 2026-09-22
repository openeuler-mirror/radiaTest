<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0032：Update 测试流水线

## 状态

已接受(Accepted)。

> 注：本 ADR 是 update 测试流水线的高层决策。后续执行模型取舍与"流水线通用化"（表/模型/API 去 `update_` 前缀、`pipeline_type` 字段、update 作为首个类型）见 [ADR 0033](./0033-update-pipeline-execution-model.md)，产品行为见 [spec 0003](../spec/0003-test-pipeline.md)。
>
> 物理机候选选择已由 ADR 0015 与 ADR 0029 细化；无用例包的状态已由 ADR 0037 收敛为 `NO_CASE`。本文相应的早期实现描述仅保留背景。

## 背景

radiaTest 已有 TestJob 模型支持 VM 创建、Mugen 部署和用例执行。现需在此基础上实现 openEuler update 测试流水线：每周对多个版本 × 双架构执行 5 个测试模块（docker、kernel、pkgcmd、pkgmanage、pkgserver），收集日志并展示统一看板。

原 EulerPipeline 实现存在大量环境 workaround（嵌套 VM、devicemapper、删内核模块、override Mugen 行为等），radiaTest 在正确启动的 VM 上不需要这些 workaround。

## 决策

### 1. Pipeline 作为 TestJob 之上的编排层

新增 `UpdatePipelineConfig`（可配置的版本列表、架构列表和模块模板顺序）和 `UpdatePipelineRun`（一个版本的一次执行）。一个 Pipeline Run 为每个模块×架构创建独立 TestJob，全并行执行；所有模块完成后执行日志汇集任务。

不把流水线塞进 TestJob 的 EnvSet，因为各模块的 Mugen suite、环境需求和脚本差异大。

### 2. 模块模板表

`TestModuleTemplate` 表存储每个模块的配置（suite、node_num、pre_env_script、post_env_script、case_filter 策略等）。Pipeline 创建 TestJob 时从模板复制配置。新增模块或调整脚本时改模板，不改代码。

### 3. 物理机执行模式

TestEnvNode 支持"物理机模式"：只设 `resource_id`、不设 `vm_request_id`、不创建 VM。worker 自动选择 `active` + `idle` + `arch` 匹配 + 非关键的物理资源，创建租约占用，SSH 部署 Mugen 并执行用例，测试完保留环境。

pkgcmd 和 pkgserver 的 `env_type=physical` 用例使用此模式；其余模块在 VM 上执行。

### 4. pkgcmd/pkgserver 用例预筛选

pkgcmd 和 pkgserver 不在机器上跑 `dnf list` 筛选，而是在后端解析 update 仓库的 `repodata/primary.xml.gz` 获取包列表，匹配数据库中的 Mugen 用例索引，按 `env_type` 拆分为 VM 用例集和物理机用例集，预分配到 TestJob 的 TestCaseRun。

无用例的包也创建 `skipped` 状态的 TestCaseRun，看板展示"应该测多少、实际测了多少、多少没用例"。

pkgserver 拆开 service-test 封装，逐个子用例单独执行（`mugen.sh -f service-test -r <case> -x`），和 pkgcmd 模式对称。

> **已变更（ADR 0022）**：pkgserver 不再预筛选 case，改为 pre_env 装包+分类后动态发现 case_list，`execute_env_set` 读回按 env_type 分配。分析文件（`failed_install` 等）收集到平台。

pkgmanage 的两个用例 `oe_test_pkg_manager01` 和 `oe_test_pkg_manager02` 必须分开执行（包管理测试留下脏状态），每个用例需要双节点（control + peer）。模块模板配置为 `env_set_num=2`、`node_num=2`，case_planner 把两个用例分别分配到两个 EnvSet，共 4 台 VM 每版本+架构。

### 5. VM 全保留 + 日志后收集

流水线执行期间不销毁 VM。每个模块跑完后在 VM 本地整理日志到约定路径（`/tmp/module-logs/`）。所有模块完成后，日志汇集任务 SSH 到各台机器拉取整理好的日志和目录，存到 radiaTest 服务器共享卷。普通文件走 `cat` + `store_artifact`；目录（如 pkgmanage 的 `pkg_manager_folder`）走 `scp -r` + `store_dir_artifact`，以文件夹形式保留在共享卷，通过浏览 API 查看文件列表和单文件内容。VM 保留到 update 发版后人工统一销毁。

### 6. 挂死检测和诊断

Worker 执行 Mugen 用例时启动后台心跳线程（30s 间隔），连续 3 次失败（90s）判定 VM 挂死。挂死时 SSH 到 VM 宿主机执行 `virsh console` / `virsh domstate` 抓取 console 诊断输出（kernel panic / OOM 信息），保存为辅助日志。物理机使用 BMC IPMI serial console 对称处理。（挂死判定与中断语义已被 [ADR 0016](0016-hang-detector-self-heal.md)、[ADR 0042](0042-physical-hang-confirmation-and-bmc-forensics.md) 与 [ADR 0044](0044-physical-hang-bmc-cross-check-watch-mode.md) 逐层修订，以各后续 ADR 为准。）

### 7. 子用例解析

Worker 在 Mugen 执行后解析模块内部的子测试结果（LTP 上千个子用例、pkgcmd 每包 pass/fail、pkgserver 每服务 pass/fail），存入 `TestCaseRunDetail` 表。看板支持 Pipeline → 模块 → Mugen 用例 → 子用例 → 日志的多级下钻。

### 8. 看板

Web UI 替代 CSV。Pipeline 详情页展示模块×架构矩阵，每格 pass/fail/skip 计数和状态色块。点击下钻到 Mugen 用例列表 → 子用例列表 → 详细日志和辅助日志在线查看。

### 9. 调度

手动触发为主，admin 在 Web UI 选择版本+架构或全量触发。保留 `POST /api/v1/update-pipelines/trigger` API 接口供外部脚本自动调用（监测到 update 仓库出现新目录或解析转测邮件后触发）。radiaTest 不做主动监测。

## 影响

- 新增后端模块 `modules/pipelines/`
- 扩展 `test_management` 支持物理机执行和挂死检测
- 新增前端 `views/update-pipelines/` 看板
- 数据库新增 5 张表 + 2 个字段扩展
- Pipeline 执行期间 VM 全保留，全并行时 5 版本 × 2 架构 × ~16 台/组 ≈ 160 台 VM 峰值，需要足够的 VM 宿主资源
- Worker 并发数需要调高以支持全并行（10 组 × ~5 模块 = ~50 Job）

## 不采用方案

- **扩展 TestJob 塞所有模块**：模块间环境需求差异大，单 VM 环境冲突风险高
- **自动定时调度**：转测时间不固定，radiaTest 不引入后台调度组件
- **嵌套虚拟化**：radiaTest 直接创建 VM，不需要嵌套
- **CSV 导出**：CSV 只能展示 Mugen 套件级结果，无法下钻到子用例
- **EulerPipeline workaround**：devicemapper、删 SCSI 模块、override Mugen 行为、手动 anaconda_list 等全部去掉
