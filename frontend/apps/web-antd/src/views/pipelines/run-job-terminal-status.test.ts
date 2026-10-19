/*
 * Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
 * This project is licensed under the Mulan PSL v2.
 * You can use it according to the terms and conditions of the Mulan PSL v2.
 * http://license.coscl.org.cn/MulanPSL2
 */

import { describe, expect, it } from 'vitest';

import { isRunJobTerminalStatus } from './run-job-terminal-status';

describe('run job terminal status', () => {
  it('treats cancelled as terminal so detail polling can stop', () => {
    expect(isRunJobTerminalStatus('cancelled')).toBe(true);
  });

  it.each(['error', 'failed', 'succeeded'])(
    'keeps %s as terminal',
    (status) => {
      expect(isRunJobTerminalStatus(status)).toBe(true);
    },
  );

  it.each(['pending', 'preparing', 'running', undefined])(
    'keeps %s non-terminal',
    (status) => {
      expect(isRunJobTerminalStatus(status)).toBe(false);
    },
  );
});
