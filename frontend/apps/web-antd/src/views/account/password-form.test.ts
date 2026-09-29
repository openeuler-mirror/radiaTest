import { describe, expect, it } from 'vitest';

import {
  buildPasswordChangePayload,
  validatePasswordForm,
} from './password-form';

describe('password form helpers', () => {
  it('validates required fields, length, and confirmation', () => {
    expect(
      validatePasswordForm({
        confirmPassword: '',
        oldPassword: '',
        password: '',
      }),
    ).toBe('请输入旧密码和新密码');

    expect(
      validatePasswordForm({
        confirmPassword: 'short',
        oldPassword: 'old-pass',
        password: 'short',
      }),
    ).toBe('新密码至少 8 个字符');

    expect(
      validatePasswordForm({
        confirmPassword: 'new-pass-2',
        oldPassword: 'old-pass',
        password: 'new-pass-1',
      }),
    ).toBe('两次输入的新密码不一致');
  });

  it('builds the change-password api payload', () => {
    const form = {
      confirmPassword: 'new-pass',
      oldPassword: 'old-pass',
      password: 'new-pass',
    };

    expect(validatePasswordForm(form)).toBeNull();
    expect(buildPasswordChangePayload(form)).toEqual({
      old_password: 'old-pass',
      password: 'new-pass',
    });
  });
});
