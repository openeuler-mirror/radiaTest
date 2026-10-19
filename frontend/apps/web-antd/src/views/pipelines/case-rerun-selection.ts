/*
 * Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
 * This project is licensed under the Mulan PSL v2.
 * You can use it according to the terms and conditions of the Mulan PSL v2.
 * http://license.coscl.org.cn/MulanPSL2
 */

import type { PipelineTestCaseRunRecord } from '#/api';

export function defaultRerunCaseIds(cases: PipelineTestCaseRunRecord[]) {
  return cases
    .filter((item) => item.status === 'failed' && item.can_rerun)
    .map((item) => item.id);
}

export function updateRerunSelection(
  selectedIds: string[],
  caseIds: string[],
  checked: boolean,
) {
  const next = new Set(selectedIds);
  for (const id of caseIds) {
    if (checked) next.add(id);
    else next.delete(id);
  }
  return [...next];
}

export function rerunSelectAllState(
  selectedIds: string[],
  cases: PipelineTestCaseRunRecord[],
) {
  const selectable = cases.filter((item) => item.can_rerun);
  const selectedCount = selectable.filter((item) =>
    selectedIds.includes(item.id),
  ).length;
  return {
    checked: selectable.length > 0 && selectedCount === selectable.length,
    indeterminate: selectedCount > 0 && selectedCount < selectable.length,
  };
}
