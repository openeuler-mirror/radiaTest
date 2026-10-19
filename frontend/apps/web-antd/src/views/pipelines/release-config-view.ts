/*
 * Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
 * This project is licensed under the Mulan PSL v2.
 * You can use it according to the terms and conditions of the Mulan PSL v2.
 * http://license.coscl.org.cn/MulanPSL2
 */

import type { KernelVariantRecord, MugenCaseRecord } from '#/api';

import { groupCasesBySuite } from '../test-jobs/test-job-view';

/**
 * release 配置的 case 选择逻辑（纯函数，便于测试）。
 *
 * 选择语义：选中 suite 默认全选其 case；精细取消后为子集。
 * 提交语义：全选发空数组（后端等价全选），子集发显式列表。
 */

/**
 * 多架构内核变体取交集：变体段名跨架构一致，仅保留在所有选中架构下都可用的变体。
 * 任一架构列表为空 → 交集为空（无法选定变体，留空不换内核）。
 */
export function intersectKernelVariants(
  perArch: KernelVariantRecord[][],
): KernelVariantRecord[] {
  if (perArch.length === 0) return [];
  const first = perArch[0];
  if (!first || first.length === 0) return [];
  const sets = perArch.map((list) => new Set(list.map((v) => v.variant)));
  return first.filter((v) => sets.every((s) => s.has(v.variant)));
}

/** 某 suite 是否当前全选。 */
export function isSuiteFullySelected(
  selected: string[] | undefined,
  allCases: string[],
): boolean {
  return (
    allCases.length > 0 &&
    (selected?.length ?? 0) === allCases.length &&
    allCases.every((c) => selected?.includes(c) ?? false)
  );
}

/**
 * 把已选状态构建为后端 case_selections 载荷。
 * 全选 → case_names: []；子集 → case_names: 显式列表。
 */
export function buildReleaseCaseSelections(
  selectedCases: Record<string, string[]>,
  cases: MugenCaseRecord[],
): { case_names: string[]; suite_name: string }[] {
  const grouped = groupCasesBySuite(cases);
  return Object.keys(selectedCases).map((suite) => {
    const all = (grouped.get(suite) ?? []).map((c) => c.case_name);
    const sel = selectedCases[suite] ?? [];
    return {
      case_names: isSuiteFullySelected(sel, all) ? [] : sel,
      suite_name: suite,
    };
  });
}
