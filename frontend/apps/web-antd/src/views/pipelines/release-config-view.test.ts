/*
 * Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
 * This project is licensed under the Mulan PSL v2.
 * You can use it according to the terms and conditions of the Mulan PSL v2.
 * http://license.coscl.org.cn/MulanPSL2
 */

import type { KernelVariantRecord, MugenCaseRecord } from '#/api';

import { describe, expect, it } from 'vitest';

import {
  buildReleaseCaseSelections,
  intersectKernelVariants,
  isSuiteFullySelected,
} from './release-config-view';

function makeVariant(variant: string, prefix: string): KernelVariantRecord {
  return { kernel_version_prefix: prefix, variant };
}

function makeCase(
  suite: string,
  caseName: string,
  nodeNum = 1,
): MugenCaseRecord {
  return {
    add_disk_num: 0,
    add_nic_num: 0,
    case_name: caseName,
    commit_sha: 'abc',
    env_type: 'vm',
    id: `${suite}-${caseName}`,
    node_num: nodeNum,
    suite_name: suite,
    synced_at: '',
  };
}

describe('isSuiteFullySelected', () => {
  it('全选返回 true', () => {
    const all = ['a', 'b', 'c'];
    expect(isSuiteFullySelected(['a', 'b', 'c'], all)).toBe(true);
    expect(isSuiteFullySelected(['c', 'a', 'b'], all)).toBe(true); // 顺序无关
  });

  it('子集或未选返回 false', () => {
    const all = ['a', 'b', 'c'];
    expect(isSuiteFullySelected(['a', 'b'], all)).toBe(false);
    expect(isSuiteFullySelected([], all)).toBe(false);
    expect(isSuiteFullySelected(undefined, all)).toBe(false);
  });

  it('无 case 的 suite 不算全选', () => {
    expect(isSuiteFullySelected([], [])).toBe(false);
  });
});

describe('buildReleaseCaseSelections', () => {
  const cases = [
    makeCase('smoke', 'oe_test_a'),
    makeCase('smoke', 'oe_test_b'),
    makeCase('ltp', 'oe_test_ltp'),
  ];

  it('全选的 suite 发空 case_names（后端等价全选）', () => {
    const selected = {
      smoke: ['oe_test_a', 'oe_test_b'],
    };
    const result = buildReleaseCaseSelections(selected, cases);
    expect(result).toEqual([{ case_names: [], suite_name: 'smoke' }]);
  });

  it('子集发显式 case 列表', () => {
    const selected = { smoke: ['oe_test_a'] };
    const result = buildReleaseCaseSelections(selected, cases);
    expect(result).toEqual([
      { case_names: ['oe_test_a'], suite_name: 'smoke' },
    ]);
  });

  it('多 suite 各自判定全选/子集', () => {
    const selected = {
      ltp: ['oe_test_ltp'], // 全选 → []
      smoke: ['oe_test_a'], // 子集 → 显式
    };
    const result = buildReleaseCaseSelections(selected, cases);
    const bySuite = Object.fromEntries(
      result.map((r) => [r.suite_name, r.case_names]),
    );
    expect(bySuite.ltp).toEqual([]);
    expect(bySuite.smoke).toEqual(['oe_test_a']);
  });

  it('无选择返回空数组', () => {
    expect(buildReleaseCaseSelections({}, cases)).toEqual([]);
  });
});

describe('intersectKernelVariants', () => {
  it('取多架构可用变体的交集', () => {
    const arm = [
      makeVariant('26.09-with-kernel-6.18', '6.18'),
      makeVariant('26.09-with-kernel-6.6', '6.6'),
    ];
    const x86 = [
      makeVariant('26.09-with-kernel-6.18', '6.18'),
      makeVariant('26.09-with-kernel-6.12', '6.12'),
    ];
    const result = intersectKernelVariants([arm, x86]);
    expect(result.map((v) => v.variant)).toEqual(['26.09-with-kernel-6.18']);
  });

  it('某架构无变体 → 交集为空', () => {
    const arm = [makeVariant('26.09-with-kernel-6.18', '6.18')];
    expect(intersectKernelVariants([arm, []])).toEqual([]);
  });

  it('无架构 → 空数组', () => {
    expect(intersectKernelVariants([])).toEqual([]);
  });

  it('全部共有 → 全保留', () => {
    const a = [makeVariant('v1', '1'), makeVariant('v2', '2')];
    expect(intersectKernelVariants([a, a, a]).map((v) => v.variant)).toEqual([
      'v1',
      'v2',
    ]);
  });
});
