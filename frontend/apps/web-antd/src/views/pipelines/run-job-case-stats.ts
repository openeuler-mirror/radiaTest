/*
 * Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
 * This project is licensed under the Mulan PSL v2.
 * You can use it according to the terms and conditions of the Mulan PSL v2.
 * http://license.coscl.org.cn/MulanPSL2
 */

import type { PipelineTestCaseRunRecord } from '#/api';

// 已出结果的状态。pending/running 尚未出结果，not_executed/no_case 不会跑，均不计入。
const FINISHED_STATUSES = new Set([
  'error',
  'failed',
  'passed',
  'skipped',
  'timeout',
]);

/** 分组头"执行中 a/x"的 a：已出结果数，失败/超时/异常/跳过都算入进度。 */
export function finishedCaseCount(cases: PipelineTestCaseRunRecord[]) {
  return cases.filter((c) => FINISHED_STATUSES.has(c.status)).length;
}

/** 统计卡"总计"口径：mugen 用例数，排除 no_case（未找到用例的包，包维度归"包行"），保证总计等于各状态计数之和。 */
export function totalCaseCount(cases: PipelineTestCaseRunRecord[]) {
  return cases.filter((c) => c.status !== 'no_case').length;
}
