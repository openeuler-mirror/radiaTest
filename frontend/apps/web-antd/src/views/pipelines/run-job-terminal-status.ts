/*
 * Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
 * This project is licensed under the Mulan PSL v2.
 * You can use it according to the terms and conditions of the Mulan PSL v2.
 * http://license.coscl.org.cn/MulanPSL2
 */

const TERMINAL_RUN_JOB_STATUSES = new Set([
  'cancelled',
  'error',
  'failed',
  'succeeded',
]);

/**
 * Determines whether the detail page can stop refreshing a RunJob.
 *
 * This set must remain aligned with the backend Pipeline RunJob terminal states.
 */
export function isRunJobTerminalStatus(
  status: null | string | undefined,
): boolean {
  return (
    status !== undefined &&
    status !== null &&
    TERMINAL_RUN_JOB_STATUSES.has(status)
  );
}
