/*
 * Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
 * This project is licensed under the Mulan PSL v2.
 * You can use it according to the terms and conditions of the Mulan PSL v2.
 * http://license.coscl.org.cn/MulanPSL2
 */

import type { PipelineTestCaseRunRecord } from '#/api';

import { describe, expect, it } from 'vitest';

import { finishedCaseCount, totalCaseCount } from './run-job-case-stats';

function caseRun(status: string): PipelineTestCaseRunRecord {
  return {
    can_rerun: false,
    case_name: status,
    env_set_id: 'env-1',
    env_set_index: 1,
    env_type: 'vm',
    exit_code: null,
    id: status,
    rerun_root_case_run_id: null,
    rerun_source_case_run_id: null,
    rerun_unavailable_reason: null,
    status,
    stderr_summary: null,
    stdout_summary: null,
    sub_cases: [],
    suite_name: 'suite-a',
  };
}

describe('run job case stats', () => {
  it('counts finished cases including failed, timeout and error', () => {
    expect(
      finishedCaseCount(
        [
          'passed',
          'failed',
          'timeout',
          'error',
          'skipped',
          'pending',
          'running',
          'not_executed',
          'no_case',
        ].map((status) => caseRun(status)),
      ),
    ).toBe(5);
  });

  it('totals mugen cases excluding no_case packages', () => {
    expect(
      totalCaseCount(
        ['passed', 'failed', 'pending', 'not_executed', 'no_case'].map(
          (status) => caseRun(status),
        ),
      ),
    ).toBe(4);
  });
});
