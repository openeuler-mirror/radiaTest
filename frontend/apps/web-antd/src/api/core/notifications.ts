import type { PageParams, PaginatedResponse } from './pagination';

import { requestClient } from '#/api/request';

export interface NotificationRecord {
  body: string;
  created_at: string;
  id: string;
  notification_type: string;
  read_at: null | string;
  target_id: null | string;
  target_type: null | string;
  target_url: null | string;
  title: string;
}

export interface NotificationUnreadCount {
  count: number;
}

export async function getNotificationsApi(params: PageParams) {
  return requestClient.get<PaginatedResponse<NotificationRecord>>(
    '/notifications',
    { params },
  );
}

export async function getNotificationUnreadCountApi() {
  return requestClient.get<NotificationUnreadCount>(
    '/notifications/unread-count',
  );
}

export async function markNotificationReadApi(notificationId: string) {
  return requestClient.request<NotificationRecord>(
    `/notifications/${notificationId}/read`,
    { method: 'PATCH' },
  );
}

export async function markAllNotificationsReadApi() {
  return requestClient.post<NotificationUnreadCount>('/notifications/read-all');
}
