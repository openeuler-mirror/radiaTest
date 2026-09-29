import type { PasswordChangePayload } from '#/api';

export interface PasswordFormState {
  confirmPassword: string;
  oldPassword: string;
  password: string;
}

export function validatePasswordForm(form: PasswordFormState) {
  if (!form.oldPassword || !form.password) {
    return '请输入旧密码和新密码';
  }
  if (form.password.length < 8) {
    return '新密码至少 8 个字符';
  }
  if (form.password !== form.confirmPassword) {
    return '两次输入的新密码不一致';
  }
  return null;
}

export function buildPasswordChangePayload(
  form: PasswordFormState,
): PasswordChangePayload {
  return {
    old_password: form.oldPassword,
    password: form.password,
  };
}
