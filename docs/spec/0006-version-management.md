<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# Spec 0006：版本管理功能规格(Version Management)

## 状态

有效(Active)。

## 目标

Kronos 提供 RC 版本测试管理能力：以"版本 → RC 里程碑（轮次）→ 轮次测试控制台"组织待发布版本的测试活动。轮次控制台承载该轮的全部测试输入与进展：软件包比对（本轮实做）、用例筛选（按比对变更包匹配 Mugen 用例并触发流水线，可扩展）、测试模块（与 update 测试一致的模块型测试，可扩展）。架构取舍见 [ADR 0045](../adr/0045-rc-version-management-package-compare.md)。

## 用户和角色

`ADMIN` 和 `TSE`：

- 创建、编辑、删除版本和里程碑。

`TE` / `TSE` / `ADMIN`（登录用户）：

- 查看版本、里程碑与比对结果。
- 触发软件包比对。
- 导出比对结果（CSV 与交付 ZIP）。

## 领域概念

- **版本(Version)**：一个待发布版本的长期对象，`name` 与 `physical_install_images.os_version` 同约定（带 `openEuler-` 前缀），如 `openEuler-26.09-DevStation`。状态为 `testing`（测试中）或 `finished`（已结束）。版本由迁移从物理机安装源的去重 `os_version` 回填。
- **里程碑(Milestone)**：版本下的一个 RC 轮次（`alpha` / `round1`… / `release`），与 PXE 装机的 `round` 语义相同。里程碑登记**比对构建根 URL**（指向 `121.36.84.172/dailybuild/EBS-<product>/<round>/<kernel-variant>/`），程序据此拼 `everything` / `EPOL/main` / `source` 及各架构清单。`pxe_round_label` 从 URL 自动推导（如 `rc4_openeuler-2026-09-07-…`），仅用于"该轮 94 是否有装机源"只读提示。创建版本时指定 RC 轮次数 N，自动生成 `alpha` + `rc1…rcN`（共 N+1 个）里程碑：命名与交付一致，比对基准链到前一轮，每轮 7 天从版本开始日期顺排，构建 URL 按命名规则自动生成为通配模板（如 `…/rc4_openeuler-*/*-with-kernel-6.6/`，内核变体取该版本的基础内核变体配置），抓取时列目录解析为最新匹配构建，亦可人工编辑为精确 URL。
- **边界不变量**：里程碑的比对 URL 与 PXE 装机源互不混用——PXE 装机继续读取 `physical_install_images`（94 内网 OS 树），`physical_install_images` 不因本功能做任何改动。

## 功能需求

### 版本管理页

- 路由 `/versions`。顶部 Tab：`RC 版本`（实做）与 `Update 版本`（占位，展示"规划中"空态）。
- 版本列表：版本 / 版本类型 / 状态 / RC 轮次数 / 起止时间 / 操作（查看、删除）。删除在有里程碑时被后端拒绝（409）。
- 新建版本：名称（必填）、版本类型（INNOVATION/LTS/LTS-SPx）、RC 轮次数（默认 0；生成 alpha + rc1…rcN，每轮 7 天自动排期，构建 URL 自动生成可后续编辑）、起止时间、备注。

### 版本详情页

- 路由 `/versions/<版本 ID>`。展示版本元信息与里程碑列表：轮次 / 起止时间 / 比对基准 / kernel 变体 / 最新比对（状态+变更数）/ 94 装机源（有/无只读提示）/ 操作。
- 操作列「测试管理」进入轮次测试控制台；「删除」在有比对记录或被引用为比对基准时被后端拒绝（409）。
- 创建里程碑：轮次名称（默认自动生成 `roundN`）、起止时间、kernel 变体、比对基准（默认前一轮）、比对构建根 URL（必填，含前缀白名单与结构校验）、轮次标签自动推导展示。

### 轮次测试控制台

- 路由 `/versions/<版本 ID>/milestones/<里程碑 ID>`。四个 Tab：
  - **软件包比对**（实做）：选择比对基准（默认该里程碑配置的前一轮）→ 触发异步比对（Celery）→ 轮询状态 → 结果展示。同对里程碑已有进行中比对时重复触发返回 409。
  - **测试进展**：占位。汇总引例测试 / 模块型测试的执行状态，由后续流水线执行回填。
  - **用例筛选**：占位。按比对变更包匹配 Mugen 用例（`suite_name == 包名`，systemd 服务转 `oe_test_service_*`）并触发流水线。
  - **测试模块**：占位。模块型测试的登记与执行。

### 软件包比对

- **比对范围**：`everything` + `EPOL/main` + `source`，与 radiaTest 交付口径一致；round 型天然不含 `update`。
- **四类比对内容**：二进制（轮次间同 `name.arch` 对比）、源码（轮次间 src rpm 对比）、同名异构（同一轮内 x86_64 vs aarch64 同名包）、重复包（同名同架构多版本并存，仅 everything 出交付文件）。
- **清单来源**：公网 dailybuild（`rc_dailybuild_base_url` 配置，默认 `http://121.36.84.172/dailybuild/EBS-`），目录列表 `title=`/`href=` 双正则抓取；清单按构建落磁盘缓存，有缓存不重复抓。`source` 缺失（404）时该块跳过，不中断比对。
- **比对语义**：与交付工具 `pkg_compare`（radiaTest 生产 `compare_str_version`）逐字一致；状态为 `SAME` / `VER_UP` / `VER_DOWN` / `REL_UP` / `REL_DOWN` / `ADD` / `DEL` / `DIFFERENT` / `LACK`。
- **存储**：数据库只存非 `SAME` 变更行，`pkg_name` 为 spec 裸包名（作为后续 Mugen 用例匹配键）；`REPEAT` 行展示用存 `name.arch`。
- **结果展示**：按「比对内容 / 仓库 / 架构 / 变更」筛选 + 分页；汇总卡按当前筛选实时计算；有删除 / 降级时展示高关注提示。
- **导出**：CSV（当前筛选的全量变更集）与交付 ZIP（7 个 `.xls`，全量含 `SAME`，命名与 `pkg_compare` 交付一致：everything 与 EPOL_main 各出 binary/source/同名异构，everything 另出 same-binary）。交付 ZIP 同时落 `rc_export_dir` 留档。

## API

前缀 `/api/v1`。写操作（POST/PUT/DELETE）仅 `TSE`/`ADMIN`；查询/触发比对/导出登录即可。

| 方法 | 路径 | 说明 |
| --- | --- | --- |
| GET | `/versions?search=&page=` | 版本分页列表（每页 50） |
| POST | `/versions` | 新建版本 |
| GET | `/versions/{id}` | 版本详情（含轮次数） |
| PUT | `/versions/{id}` | 编辑版本 |
| DELETE | `/versions/{id}` | 删除版本（有里程碑返回 409） |
| GET | `/versions/{id}/milestones` | 版本下里程碑列表 |
| POST | `/milestones` | 创建里程碑 |
| PUT | `/milestones/{id}` | 编辑里程碑 |
| DELETE | `/milestones/{id}` | 删除里程碑（有比对记录或被引为基准返回 409） |
| POST | `/milestones/{id}/compares` | 触发比对，body `{base_milestone_id}`，返回 202；任一轮次未登记构建根 URL 返回 400 |
| GET | `/compares/{id}` | 比对任务状态与汇总 |
| GET | `/compares/{id}/results` | 变更结果，支持 `kind/repo_path/arch/status`（多值）筛选 |
| GET | `/compares/{id}/export` | 导出交付 ZIP（比对未完成返回 409） |

错误沿用统一 API 错误契约（[平台运行时规格](0005-platform-runtime.md)）：404 不存在、403 无权限、409 冲突（重复 / 有子资源 / 进行中）、400 参数错误。

## 验收标准

1. 登录后左侧菜单出现「版本管理」，不再出现「流水线类型」；`GET /api/v1/pipelines/types` 仍可用（测试模块模板创建的类型下拉正常）。
2. 版本列表展示回填的历史 `os_version`；可新建版本并在有里程碑时删除被拒（409 提示）。
3. 创建里程碑后列表可见轮次标签与 94 装机源提示；94 已登记该轮 OS 树的显示"有"。
4. 对同版本两个轮次触发比对：任务异步执行后状态 `succeeded`，结果各状态计数与 `pkg_compare` 交付一致（如 openEuler-26.09-DevStation rc3-vs-rc4 everything：SAME 22401 / VER_UP 469 / REL_UP 461 / ADD 117 / DEL 27；同名异构 LACK 186；EPOL ADD 2038）。
5. 结果页筛选 / 分页 / 汇总卡正确联动；导出 ZIP 解压为 7 个 xls，内容与交付工具输出逐项一致。
6. `TE` 用户触发比对和导出可用，创建 / 删除版本或里程碑被拒（403）。