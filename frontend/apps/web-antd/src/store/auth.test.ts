import { useAccessStore, useUserStore } from '@vben/stores';

import { createPinia, setActivePinia } from 'pinia';
import { beforeEach, describe, expect, it, vi } from 'vitest';

import { useAuthStore } from './auth';

const api = vi.hoisted(() => ({
  getUserInfoApi: vi.fn(),
  loginApi: vi.fn(),
  logoutApi: vi.fn(),
}));

vi.mock('#/api', () => api);
vi.mock('vue-router', () => ({
  useRouter: () => ({
    currentRoute: { value: { fullPath: '/' } },
    push: vi.fn(),
    replace: vi.fn(),
  }),
}));
vi.mock('@vben/preferences', () => ({
  preferences: { app: { defaultHomePath: '/' } },
}));
vi.mock('ant-design-vue', () => ({
  notification: { success: vi.fn() },
}));
vi.mock('#/locales', () => ({ $t: (key: string) => key }));

describe('auth store', () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
  });

  it('clears the partial login state when loading user info fails', async () => {
    api.loginApi.mockResolvedValue({ accessToken: 'access-token' });
    api.getUserInfoApi.mockRejectedValue(new Error('user info unavailable'));
    const accessStore = useAccessStore();
    const userStore = useUserStore();
    const authStore = useAuthStore();

    userStore.setUserInfo({
      avatar: '',
      realName: 'Old User',
      roles: ['TE'],
      userId: 'old-user',
      username: 'old-user',
    });
    accessStore.setAccessCodes(['TE']);

    await expect(authStore.authLogin({})).rejects.toThrow(
      'user info unavailable',
    );

    expect(accessStore.accessToken).toBeNull();
    expect(accessStore.accessCodes).toEqual([]);
    expect(userStore.userInfo).toBeNull();
  });
});
