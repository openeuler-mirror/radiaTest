import { describe, expect, it } from 'vitest';

import { buildVNCOptions } from './console-options';

describe('buildVNCOptions', () => {
  it('sets the binary websocket subprotocol required by QEMU VNC websocket', () => {
    expect(buildVNCOptions({ password: null })).toEqual({
      wsProtocols: ['binary'],
    });
  });

  it('keeps VNC credentials when a password is configured', () => {
    expect(buildVNCOptions({ password: 'secret' })).toEqual({
      credentials: { password: 'secret' },
      wsProtocols: ['binary'],
    });
  });
});
