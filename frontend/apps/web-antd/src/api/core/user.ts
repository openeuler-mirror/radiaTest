import type { UserInfo } from '@vben/types';

import { requestClient } from '#/api/request';

interface CurrentUserResponse {
  display_name: null | string;
  id: string;
  is_active: boolean;
  last_login_at: null | string;
  role: 'ADMIN' | 'TE' | 'TSE';
  username: string;
  created_at: string;
}

export type UserRole = 'ADMIN' | 'TE' | 'TSE';

export interface UserRecord {
  created_at: string;
  display_name: null | string;
  id: string;
  is_active: boolean;
  last_login_at: null | string;
  role: UserRole;
  username: string;
}

export interface UserListParams {
  display_name?: string;
  is_active?: boolean;
  limit?: number;
  offset?: number;
  role?: UserRole;
  username?: string;
}

export interface UserCreatePayload {
  display_name?: null | string;
  password: string;
  role: UserRole;
  username: string;
}

export interface UserUpdatePayload {
  display_name?: null | string;
  is_active?: boolean;
  role?: UserRole;
}

export interface PasswordResetPayload {
  password: string;
}

export interface PasswordChangePayload {
  old_password: string;
  password: string;
}

/**
 * 获取用户信息
 */
export async function getUserInfoApi() {
  const user = await requestClient.get<CurrentUserResponse>('/users/me');
  return {
    avatar: '',
    desc: '',
    homePath: '/dashboard',
    realName: user.display_name || user.username,
    roles: [user.role],
    token: '',
    userId: user.id,
    username: user.username,
  } satisfies UserInfo;
}

export async function getUsersApi(params: UserListParams) {
  return requestClient.get<UserRecord[]>('/users', { params });
}

export async function createUserApi(payload: UserCreatePayload) {
  return requestClient.post<UserRecord>('/users', payload);
}

export async function updateUserApi(
  userId: string,
  payload: UserUpdatePayload,
) {
  return requestClient.request<UserRecord>(`/users/${userId}`, {
    data: payload,
    method: 'PATCH',
  });
}

export async function resetUserPasswordApi(
  userId: string,
  payload: PasswordResetPayload,
) {
  return requestClient.post<unknown>(
    `/users/${userId}/reset-password`,
    payload,
  );
}

export async function changeOwnPasswordApi(payload: PasswordChangePayload) {
  return requestClient.post<unknown>('/users/me/change-password', payload);
}
