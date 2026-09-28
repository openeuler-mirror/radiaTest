<script lang="ts" setup>
import { computed } from 'vue';
import { useRouter } from 'vue-router';

import { AuthenticationLoginExpiredModal } from '@vben/common-ui';
import { BasicLayout, LockScreen, UserDropdown } from '@vben/layouts';
import { preferences } from '@vben/preferences';
import { useAccessStore, useUserStore } from '@vben/stores';

import { useAuthStore } from '#/store';
import LoginForm from '#/views/_core/authentication/login.vue';

import NotificationCenter from './notification-center.vue';

const userStore = useUserStore();
const authStore = useAuthStore();
const accessStore = useAccessStore();
const router = useRouter();

const avatar = computed(() => {
  return userStore.userInfo?.avatar || preferences.app.defaultAvatar;
});

const roleText = computed(() => {
  return userStore.userInfo?.roles?.join(', ') || '';
});

const userMenus = computed(() => [
  {
    handler: () => router.push('/account'),
    icon: 'lucide:user-round',
    text: '我的账号',
  },
]);

async function handleLogout() {
  await authStore.logout(false);
}
</script>

<template>
  <BasicLayout @clear-preferences-and-logout="handleLogout">
    <template #notification>
      <NotificationCenter />
    </template>
    <template #user-dropdown>
      <UserDropdown
        :avatar
        :description="roleText"
        :menus="userMenus"
        :text="userStore.userInfo?.realName"
        @clear-preferences-and-logout="handleLogout"
        @logout="handleLogout"
      />
    </template>
    <template #extra>
      <AuthenticationLoginExpiredModal
        v-model:open="accessStore.loginExpired"
        :avatar
      >
        <LoginForm />
      </AuthenticationLoginExpiredModal>
    </template>
    <template #lock-screen>
      <LockScreen :avatar @to-login="handleLogout" />
    </template>
  </BasicLayout>
</template>
