<script lang="ts" setup>
import type { NotificationRecord } from '#/api';

import { onMounted, ref, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Bell, MailCheck, RotateCw } from '@vben/icons';

import {
  Badge,
  Button,
  Drawer,
  Empty,
  message,
  Pagination,
  Spin,
  Tooltip,
} from 'ant-design-vue';
import dayjs from 'dayjs';

import {
  getNotificationsApi,
  getNotificationUnreadCountApi,
  markAllNotificationsReadApi,
  markNotificationReadApi,
} from '#/api';

const route = useRoute();
const router = useRouter();
const open = ref(false);
const loading = ref(false);
const notifications = ref<NotificationRecord[]>([]);
const page = ref(1);
const total = ref(0);
const unreadCount = ref(0);

function displayTime(value: string) {
  return dayjs(value).format('YYYY-MM-DD HH:mm');
}

async function loadUnreadCount() {
  try {
    const result = await getNotificationUnreadCountApi();
    unreadCount.value = result.count;
  } catch {
    // The global request handler reports authentication and network errors.
  }
}

async function loadNotifications() {
  loading.value = true;
  try {
    const result = await getNotificationsApi({ page: page.value });
    notifications.value = result.items;
    total.value = result.total;
    await loadUnreadCount();
  } finally {
    loading.value = false;
  }
}

async function showNotifications() {
  open.value = true;
  await loadNotifications();
}

async function markAllRead() {
  await markAllNotificationsReadApi();
  message.success('通知已全部标记为已读');
  await loadNotifications();
}

async function openNotification(notification: NotificationRecord) {
  if (!notification.read_at) {
    await markNotificationReadApi(notification.id);
    unreadCount.value = Math.max(0, unreadCount.value - 1);
  }
  open.value = false;
  if (notification.target_url) {
    await router.push(notification.target_url);
  }
}

async function changePage(nextPage: number) {
  page.value = nextPage;
  await loadNotifications();
}

onMounted(() => {
  void loadUnreadCount();
});

watch(
  () => route.fullPath,
  () => {
    void loadUnreadCount();
  },
);
</script>

<template>
  <div class="notification-trigger">
    <Tooltip title="通知">
      <Badge :count="unreadCount" :overflow-count="99" size="small">
        <Button
          aria-label="通知"
          class="notification-button"
          type="text"
          @click="showNotifications"
        >
          <Bell class="size-4" />
        </Button>
      </Badge>
    </Tooltip>
  </div>

  <Drawer
    v-model:open="open"
    class="notification-drawer"
    placement="right"
    title="通知"
    width="min(440px, 100vw)"
  >
    <template #extra>
      <div class="notification-actions">
        <Tooltip title="刷新">
          <Button aria-label="刷新通知" type="text" @click="loadNotifications">
            <RotateCw class="size-4" />
          </Button>
        </Tooltip>
        <Tooltip title="全部已读">
          <Button
            aria-label="全部已读"
            :disabled="unreadCount === 0"
            type="text"
            @click="markAllRead"
          >
            <MailCheck class="size-4" />
          </Button>
        </Tooltip>
      </div>
    </template>

    <Spin :spinning="loading">
      <div v-if="notifications.length > 0" class="notification-list">
        <button
          v-for="item in notifications"
          :key="item.id"
          class="notification-item"
          :class="{ unread: !item.read_at }"
          type="button"
          @click="openNotification(item)"
        >
          <span v-if="!item.read_at" class="unread-dot"></span>
          <span class="notification-content">
            <strong>{{ item.title }}</strong>
            <span class="notification-body">{{ item.body }}</span>
            <time>{{ displayTime(item.created_at) }}</time>
          </span>
        </button>
      </div>
      <Empty v-else description="暂无通知" />
    </Spin>

    <template #footer>
      <div class="notification-pagination">
        <Pagination
          :current="page"
          :page-size="50"
          :show-size-changer="false"
          :total="total"
          @change="changePage"
        />
      </div>
    </template>
  </Drawer>
</template>

<style scoped>
.notification-trigger {
  display: flex;
  align-items: center;
  height: 100%;
  margin-right: 8px;
}

.notification-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
}

.notification-actions {
  display: flex;
  gap: 4px;
}

.notification-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.notification-item {
  position: relative;
  display: flex;
  width: 100%;
  min-width: 0;
  padding: 12px 14px;
  color: inherit;
  text-align: left;
  cursor: pointer;
  background: transparent;
  border: 1px solid var(--ant-color-border, #d9d9d9);
  border-radius: 6px;
}

.notification-item:hover,
.notification-item.unread {
  background: var(--ant-color-fill-tertiary, rgb(0 0 0 / 4%));
}

.unread-dot {
  flex: 0 0 auto;
  width: 8px;
  height: 8px;
  margin: 6px 10px 0 0;
  background: var(--ant-color-primary, #1677ff);
  border-radius: 50%;
}

.notification-content {
  display: flex;
  flex: 1 1 auto;
  flex-direction: column;
  gap: 6px;
  min-width: 0;
}

.notification-content strong,
.notification-body,
.notification-content time {
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.notification-body,
.notification-content time {
  font-size: 13px;
  color: var(--ant-color-text-secondary, rgb(0 0 0 / 65%));
}

.notification-pagination {
  display: flex;
  justify-content: flex-end;
  min-width: 0;
  overflow-x: auto;
}
</style>
