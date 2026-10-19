/*
 * Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
 * This project is licensed under the Mulan PSL v2.
 * You can use it according to the terms and conditions of the Mulan PSL v2.
 * http://license.coscl.org.cn/MulanPSL2
 */

import type { PipelineTestCaseRunRecord } from '#/api';

import { describe, expect, it } from 'vitest';

import {
  defaultRerunCaseIds,
  rerunSelectAllState,
  updateRerunSelection,
} from './case-rerun-selection';

function caseRun(
  id: string,
  status: string,
  canRerun = true,
): PipelineTestCaseRunRecord {
  return {
    can_rerun: canRerun,
    case_name: id,
    env_set_id: 'env-1',
    env_set_index: 1,
    env_type: 'vm',
    exit_code: null,
    id,
    rerun_root_case_run_id: null,
    rerun_source_case_run_id: null,
    rerun_unavailable_reason: canRerun ? null : '环境不可用',
    status,
    stderr_summary: null,
    stdout_summary: null,
    sub_cases: [],
    suite_name: 'suite-a',
  };
}

describe('case rerun selection', () => {
  it('defaults to available failed cases only', () => {
    expect(
      defaultRerunCaseIds([
        caseRun('failed', 'failed'),
        caseRun('passed', 'passed'),
        caseRun('unavailable', 'failed', false),
      ]),
    ).toEqual(['failed']);
  });

  it('updates one suite without clearing extra selections', () => {
    expect(
      updateRerunSelection(['extra'], ['failed-a', 'failed-b'], true),
    ).toEqual(['extra', 'failed-a', 'failed-b']);
    expect(
      updateRerunSelection(
        ['extra', 'failed-a', 'failed-b'],
        ['failed-a', 'failed-b'],
        false,
      ),
    ).toEqual(['extra']);
  });

  it('reports checked only when every selectable visible case is selected', () => {
    expect(
      rerunSelectAllState(
        ['a', 'b'],
        [caseRun('a', 'failed'), caseRun('b', 'failed')],
      ),
    ).toEqual({ checked: true, indeterminate: false });
  });

  it('reports indeterminate when only some selectable cases are selected', () => {
    expect(
      rerunSelectAllState(
        ['a'],
        [caseRun('a', 'failed'), caseRun('b', 'failed')],
      ),
    ).toEqual({ checked: false, indeterminate: true });
  });

  it('ignores non-rerunnable cases in select-all state', () => {
    expect(
      rerunSelectAllState(
        ['a'],
        [caseRun('a', 'failed'), caseRun('blocked', 'failed', false)],
      ),
    ).toEqual({ checked: true, indeterminate: false });
  });

  it('reports unchecked when nothing selectable is visible', () => {
    expect(
      rerunSelectAllState(['a'], [caseRun('blocked', 'failed', false)]),
    ).toEqual({ checked: false, indeterminate: false });
  });
});
