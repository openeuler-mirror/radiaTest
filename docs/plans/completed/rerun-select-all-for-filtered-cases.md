<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

# 用例重跑选择器全选当前筛选列表

## 状态

已完成：`rerunSelectAllState` 落地于 `case-rerun-selection.ts` 并接入 case-rerun-modal（`5dfb689`），Spec 0003 已同步全选语义。

## 背景与问题

用例重跑选择器(`case-rerun-modal.vue`)支持按状态(失败/异常/超时等)、环境套和关键词筛选候选用例,但缺少对筛选结果的全选能力:用户筛出失败用例后只能逐个勾选,或用左侧 Suite 勾选框整 Suite 选中(会把非失败状态的用例也选进来),与"挑选出某一类用例批量重跑"的操作预期不符。

## 范围

- 右侧用例列表筛选栏新增"全选"勾选框,作用范围严格限定为**当前 Suite 视图 + 当前筛选条件**(状态、环境套、Case 关键词)匹配的可见用例
- 全选只勾选 `can_rerun` 的用例,不可重跑用例(环境已释放等)保持未选
- 勾选框三态:可见可选用例全部选中时打勾、部分选中时半选、未选时为空;无可选用例时禁用
- 取消勾选只取消当前可见可选用例的选中,不影响其他 Suite 或被筛掉的已选用例
- 纯选择逻辑放入 `case-rerun-selection.ts`,保持可测

## 明确不做

- 不做跨 Suite 的全选(想选其他 Suite 时切换后再点全选)
- 不改动"恢复默认失败项"和"清空"按钮及既有选择交互
- 不新增 API、不改动后端;提交仍只提交 `can_rerun` 的用例
- 不因筛选条件变化自动清空已选草稿(维持现状)

## 实施步骤(TDD,每步先失败测试再实现)

1. `case-rerun-selection.ts` 新增 `rerunSelectAllState(selectedIds, cases)`:基于可见用例中 `can_rerun` 子集计算 `{ checked, indeterminate }`(单测覆盖全选/半选/未选/无可选用例)
2. `case-rerun-modal.vue` 接入:筛选栏加"全选"勾选框(三态、无可选用例禁用),勾选/取消通过既有 `updateRerunSelection` 作用于可见可选用例
3. Spec 0003 重跑选择器行为补一句全选语义
4. `./scripts/check.sh`

## 验证标准

- 新增单测先失败后通过;`./scripts/check.sh` 通过
- 弹窗内实测:筛"失败"点全选只选中失败可重跑用例;切 Suite/改筛选后已选草稿不被意外改动;取消全选只影响当前可见可选用例
