import { describe, expect, it, vi } from 'vitest';

import { createLatestRequestGuard } from './latest-request';

describe('createLatestRequestGuard', () => {
  it('allows only the latest request to commit state', () => {
    const guard = createLatestRequestGuard();
    const first = guard.begin();
    const second = guard.begin();
    const commit = vi.fn();

    first.commit(() => commit('first'));
    second.commit(() => commit('second'));

    expect(commit).toHaveBeenCalledOnce();
    expect(commit).toHaveBeenCalledWith('second');
  });

  it('invalidates an in-flight request without starting another one', () => {
    const guard = createLatestRequestGuard();
    const request = guard.begin();
    const commit = vi.fn();

    guard.invalidate();
    request.commit(commit);

    expect(commit).not.toHaveBeenCalled();
  });
});
