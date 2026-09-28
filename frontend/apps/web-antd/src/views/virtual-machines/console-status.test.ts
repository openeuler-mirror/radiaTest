import { describe, expect, it } from 'vitest';

import { disconnectedConsoleStatus } from './console-status';

describe('disconnectedConsoleStatus', () => {
  it('distinguishes stopped and destroyed VMs from VNC disconnection', () => {
    expect(disconnectedConsoleStatus('shut off')).toBe('stopped');
    expect(disconnectedConsoleStatus('destroyed')).toBe('destroyed');
    expect(disconnectedConsoleStatus('running')).toBe('disconnected');
  });
});
