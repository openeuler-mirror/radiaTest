import { describe, expect, it } from 'vitest';

import { parseAPIError } from './api-error';

describe('parseAPIError', () => {
  it('parses the API error envelope from a response error', () => {
    expect(
      parseAPIError({
        response: {
          data: {
            error: {
              code: 'resource_not_found',
              details: null,
              message: '资源不存在',
            },
          },
        },
      }),
    ).toEqual({
      code: 'resource_not_found',
      details: null,
      message: '资源不存在',
    });
  });

  it('parses a validation error envelope directly', () => {
    expect(
      parseAPIError({
        error: {
          code: 'validation_error',
          details: [{ field: 'expected_ends_at', message: '租期超过限制' }],
          message: '请求参数校验失败',
        },
      }),
    ).toEqual({
      code: 'validation_error',
      details: [{ field: 'expected_ends_at', message: '租期超过限制' }],
      message: '请求参数校验失败',
    });
  });

  it('does not accept legacy error shapes', () => {
    expect(parseAPIError({ detail: 'legacy error' })).toBeNull();
    expect(parseAPIError({ error: 'legacy error' })).toBeNull();
  });

  it('drops malformed details without rejecting the error', () => {
    expect(
      parseAPIError({
        error: {
          code: 'validation_error',
          details: [{ field: 'name' }],
          message: '请求参数校验失败',
        },
      })?.details,
    ).toBeNull();
  });
});
