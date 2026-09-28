export interface IdempotencyAttempt {
  fingerprint: string;
  key: string;
}

export function createIdempotencyAttempt(): IdempotencyAttempt {
  return { fingerprint: '', key: '' };
}

export function idempotencyKeyFor(
  attempt: IdempotencyAttempt,
  action: string,
  payload: unknown,
) {
  const fingerprint = JSON.stringify(payload);
  if (attempt.fingerprint !== fingerprint) {
    attempt.fingerprint = fingerprint;
    attempt.key = `${action}-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
  }
  return attempt.key;
}

export function resetIdempotencyAttempt(attempt: IdempotencyAttempt) {
  attempt.fingerprint = '';
  attempt.key = '';
}
