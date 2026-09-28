import { describe, expect, it } from 'vitest';

import { buildCtrlAltKeySequence, ctrlAltTargets } from './console-keys';

describe('ctrlAltTargets', () => {
  it('offers F1-F6 and Del only', () => {
    expect(ctrlAltTargets.map((target) => target.value)).toEqual([
      'F1',
      'F2',
      'F3',
      'F4',
      'F5',
      'F6',
      'Del',
    ]);
  });

  it('builds the ctrl-alt key sequence around the selected key', () => {
    expect(buildCtrlAltKeySequence('F2')).toEqual([
      { code: 'ControlLeft', down: true, keysym: 65_507 },
      { code: 'AltLeft', down: true, keysym: 65_513 },
      { code: 'F2', keysym: 65_471 },
      { code: 'AltLeft', down: false, keysym: 65_513 },
      { code: 'ControlLeft', down: false, keysym: 65_507 },
    ]);
  });

  it('returns null for unsupported targets', () => {
    expect(buildCtrlAltKeySequence('F7')).toBeNull();
  });
});
