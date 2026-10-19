/*
 * Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
 * This project is licensed under the Mulan PSL v2.
 * You can use it according to the terms and conditions of the Mulan PSL v2.
 * http://license.coscl.org.cn/MulanPSL2
 */

import type { MugenCaseRecord, TestJobTemplateRecord } from '#/api';

import { describe, expect, it } from 'vitest';

import {
  buildCaseSelections,
  buildTemplateJobName,
  buildTestJobPayload,
  buildTestJobTemplatePatch,
  findUnavailableCaseSelections,
  groupCasesBySuite,
  inferSelectionConstraints,
  isCaseSelectable,
  isValidTestJobTemplateName,
  testStatusColor,
  testStatusLabel,
  validateTestJobForm,
} from './test-job-view';

function testCase(
  suiteName: string,
  caseName: string,
  overrides: Partial<MugenCaseRecord> = {},
): MugenCaseRecord {
  return {
    add_disk_num: 0,
    add_nic_num: 0,
    case_name: caseName,
    commit_sha: 'abc123',
    env_type: 'vm',
    id: `${suiteName}-${caseName}`,
    node_num: 1,
    suite_name: suiteName,
    synced_at: '2026-07-14T00:00:00Z',
    ...overrides,
  };
}

const form = {
  arch: 'aarch64',
  dist: 'openEuler',
  envSetNum: 2,
  imageRound: 'round-9',
  keepFailedEnv: true,
  name: ' smoke ',
  osVersion: 'openEuler-24.03-LTS-SP4',
  postEnvScript: '',
  preEnvScript: ' echo ready ',
};

describe('test job selection helpers', () => {
  it('groups and sorts cases by suite', () => {
    const grouped = groupCasesBySuite([
      testCase('suite-b', 'case-2'),
      testCase('suite-a', 'case-2'),
      testCase('suite-a', 'case-1'),
    ]);

    expect([...grouped.keys()]).toEqual(['suite-a', 'suite-b']);
    expect(grouped.get('suite-a')?.map((item) => item.case_name)).toEqual([
      'case-1',
      'case-2',
    ]);
  });

  it('builds stable selections and infers maximum constraints', () => {
    const cases = [
      testCase('suite-a', 'case-1'),
      testCase('suite-a', 'case-2', {
        add_disk_num: 2,
        add_nic_num: 1,
        node_num: 2,
      }),
    ];
    const selections = buildCaseSelections({
      'suite-a': ['case-2', 'case-1', 'case-2'],
      'suite-b': [],
    });

    expect(selections).toEqual([
      { case_names: ['case-1', 'case-2'], suite_name: 'suite-a' },
    ]);
    expect(inferSelectionConstraints(cases, selections)).toEqual({
      addDiskNum: 2,
      addNicNum: 1,
      caseCount: 2,
      nodeNum: 2,
    });
  });

  it('only allows supported VM cases to be selected', () => {
    expect(isCaseSelectable(testCase('suite-a', 'case-1'))).toBe(true);
    expect(
      isCaseSelectable(testCase('suite-a', 'case-2', { node_num: 3 })),
    ).toBe(false);
    expect(
      isCaseSelectable(testCase('suite-a', 'case-3', { env_type: 'physical' })),
    ).toBe(false);
  });

  it('finds removed and newly unsupported case selections', () => {
    const cases = [
      testCase('suite-a', 'supported'),
      testCase('suite-a', 'too-many-nodes', { node_num: 3 }),
    ];

    expect(
      findUnavailableCaseSelections(cases, [
        {
          case_names: ['supported', 'too-many-nodes', 'removed'],
          suite_name: 'suite-a',
        },
      ]),
    ).toEqual(['suite-a/too-many-nodes', 'suite-a/removed']);
  });
});

describe('test job form helpers', () => {
  const selections = [{ case_names: ['case-1'], suite_name: 'suite-a' }];

  it('validates required fields and builds the API payload', () => {
    expect(validateTestJobForm({ ...form, name: '' }, selections)).toBe(
      '请输入任务名称',
    );
    expect(validateTestJobForm(form, selections)).toBeNull();
    expect(buildTestJobPayload(form, selections)).toMatchObject({
      env_set_num: 2,
      env_type: 'vm',
      framework: 'mugen',
      keep_failed_env: true,
      name: 'smoke',
      post_env_script: null,
      pre_env_script: 'echo ready',
    });
  });

  it('formats statuses consistently', () => {
    expect(testStatusLabel('preparing')).toBe('准备中');
    expect(testStatusLabel('unknown')).toBe('unknown');
    expect(testStatusColor('succeeded')).toBe('green');
    expect(testStatusColor('timeout')).toBe('orange');
    expect(testStatusColor('error')).toBe('red');
  });

  it('validates template names and builds a readable default task name', () => {
    expect(isValidTestJobTemplateName('openEuler.smoke-aarch64_1')).toBe(true);
    expect(isValidTestJobTemplateName('openEuler smoke')).toBe(false);
    expect(buildTemplateJobName('smoke', new Date(2026, 6, 15, 9, 8, 7))).toBe(
      'smoke-20260715-090807',
    );
  });

  it('builds a partial template update without overwriting unrelated fields', () => {
    const payload = buildTestJobPayload(form, selections);
    const template = {
      ...payload,
      can_manage: true,
      case_count: 1,
      created_at: '2026-07-15T00:00:00Z',
      creator_user_id: 'user-id',
      creator_username: 'te1',
      id: 1,
      is_available: true,
      post_env_script: payload.post_env_script ?? null,
      pre_env_script: payload.pre_env_script ?? null,
      suite_count: 1,
      unavailable_reason: null,
      updated_at: '2026-07-15T00:00:00Z',
    } satisfies TestJobTemplateRecord;

    expect(
      buildTestJobTemplatePatch(template, {
        ...payload,
        name: 'renamed',
      }),
    ).toEqual({ name: 'renamed' });
  });
});
