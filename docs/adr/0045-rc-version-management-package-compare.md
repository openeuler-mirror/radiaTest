<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# ADR 0045：RC 版本管理域与软件包比对语义对齐交付物

日期: 2026-09-09（fork 合并 upstream 时由 0041 改号，避开本仓库既有的 0041-vm-host-fact-reconciliation）

## 状态

已采纳。

## 背景

Kronos 只支持 update 测试。为支撑 openEuler RC 版本测试，需要"版本→RC 轮次→软件包
比对→筛选用例"这条链路里最核心的实际功能：版本与里程碑管理、两个 RC 轮次间软件包
差异比对。参照物是负责人实际工具链 `atomgit.com/zjl_long/pkg_compare`（radiaTest
`rpm_util.py` 的生产演进版）与 radiaTest 平台：交付物为 RAR 内含 7 个 xls
（everything+EPOL × binary/source/同名异构，everything 另加 same-binary），比对
语义是 radiaTest 生产 `compare_str_version`，数据源是公网
`121.36.84.172/dailybuild/EBS-<product>/…`（唯一含 source 树的位置）。

三个必须澄清的事实约束：

1. 镜像里 PR 版本的 `rpm_util`（朴素字符串比较）与本生产语义**不一致**——朴素比较
   会产生大量假 REL_DOWN（实测 rc2-vs-rc3 32 个、rc3-vs-rc4 79 个），而交付物为 0。
2. source 清单只有公网 dailybuild 有；内网 94 镜像无 source 树，不能作为比对数据源，
   但内网 94 OS 树是物理机 PXE 装机的安装源，两者**必须隔离**。
3. 物理机 PXE 装机已稳定依赖 `physical_install_images`（94 内网 OS 树），不可因新增
   比对功能而改动或混用其 URL。

## 决策

### 1. 版本管理作为独立域，四张新表

`versions`（版本）→ `milestones`（RC 轮次，挂版本）→ `rc_milestone_compares`
（比对实例）→ `rc_package_compare_results`（非 SAME 变更行）。版本从
`physical_install_images` 去重 `os_version` 回填。（2026-09-10 变更：回填取消——
历史版本不自动进入平台，版本由用户手动创建。轮次命名对齐交付习惯：第一轮
`alpha`，其后 `rc1…rcN`；创建版本时指定 RC 轮次数 N 生成 `alpha` + `rc1…rcN`
共 N+1 个轮次，每轮 7 天从版本开始日期顺排。构建 URL 按命名规则自动生成为
通配模板（`{tag}_openeuler-*` / `*-with-kernel-{基础变体}`），抓取前列目录解析为
最新匹配构建，支持人工编辑为精确 URL；`milestones.build_url` 改为可空，缺失或
解析失败时比对返回 400。原 0044 回填迁移改为 no-op 维持历史链。）里程碑只在语义上与装机轮次关联：
`pxe_round_label` 从 `build_url` 推导，用于"94 是否有装机源"只读提示；**不给
`physical_install_images` 加外键、不参与 PXE 装配流**（推翻早先 Q4 加外键草案，
避免 PXE 表任何 DDL/逻辑风险）。

### 2. 比对语义 = radiaTest 生产 compare_str_version

版本/release 比较复刻 radiaTest 生产 `compare_str_version`（分段、数字段、`oe*`
段特判）+ 多版本取高（select_high_pkg）+ `name.arch` 键 + 重复包检测，保证 Kronos
比对结果与负责人交付逐项一致（9 状态：SAME/VER_UP/VER_DOWN/REL_UP/REL_DOWN/
ADD/DEL/LACK/DIFFERENT，另 REPEAT）。**不采用 rpmvercmp 换血**：虽然版本语义更
"标准"，但会改变对外口径、破坏与交付对账。

### 3. 数据源与抓取

比对清单从可配置的 `rc_dailybuild_base_url`（默认 `121.36.84.172/dailybuild/EBS-`，
公网可达）抓取，目录列表 `title=` / `href=` 双正则，落磁盘缓存（按
(版本,轮次,repo,arch)），source 404 容忍跳过。内网 94 镜像不作为比对数据源。

### 4. 存储与导出分层

数据库只存**非 SAME 变更行**（页面/筛选轻快）；全量（含 SAME）在导出时按同一语义
现场重算，产出 zip（xlwt 7 个 .xls，格式与 `pkg_compare` 交付一致）。导出用 zip 而非
rar：浏览器端通用、避免后端依赖 rar CLI。

### 5. 执行与权限

比对用 Celery 异步任务 + redis 锁防同对并发；每次比对独立实例可回溯。权限：版本/
里程碑写操作仅 TSE/ADMIN；查看/触发比对/导出为登录即可。前端删除「流水线类型」
菜单/路由/页面，`/api/v1/pipelines/types` 后端保留。

## 不采用的方案

- **rpmvercmp 作为比对语义**：与交付口径不一致，对账失真。
- **复用 `physical_install_images` 存里程碑**（无新表）：轮次需存比对 URL、source
  视图、独立比对实例，与装机明细表职责不同；且会污染 PXE 表。
- **内网 94 镜像作为比对数据源**：无 source 树，binary 口径也可能与交付不一致。
- **比对结果全量落库**（含 SAME）：单次比对 6 万+ 行膨胀 DB，页面无价值。
- **导出 rar**：需要后端 rar CLI，浏览器兼容性差；zip 达成同一目标。
- **让里程碑 URL 同时充当 PXE 安装源**：物理机在隔离内网 PXE 启动无法访问公网
  121.36.84.172，会挂装。