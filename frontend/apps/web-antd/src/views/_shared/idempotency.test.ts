import { afterEach, describe, expect, it, vi } from 'vitest';

import {
  createIdempotencyAttempt,
  idempotencyKeyFor,
  resetIdempotencyAttempt,
} from './idempotency';

afterEach(() => vi.restoreAllMocks());

describe('idempotency attempt', () => {
  it('reuses a key for the same payload and rotates it when the payload changes', () => {
    vi.spyOn(Date, 'now').mockReturnValueOnce(1).mockReturnValueOnce(2);
    const attempt = createIdempotencyAttempt();

    const first = idempotencyKeyFor(attempt, 'vm-request', { vcpu: 2 });
    expect(idempotencyKeyFor(attempt, 'vm-request', { vcpu: 2 })).toBe(first);
    expect(idempotencyKeyFor(attempt, 'vm-request', { vcpu: 4 })).not.toBe(
      first,
    );
  });

  it('rotates the key after a successful attempt is reset', () => {
    vi.spyOn(Date, 'now').mockReturnValueOnce(1).mockReturnValueOnce(2);
    const attempt = createIdempotencyAttempt();
    const first = idempotencyKeyFor(attempt, 'extend', { endsAt: 'tomorrow' });

    resetIdempotencyAttempt(attempt);

    expect(
      idempotencyKeyFor(attempt, 'extend', { endsAt: 'tomorrow' }),
    ).not.toBe(first);
  });
});
