import { createApp } from 'vue';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import NotificationCenter from './notification-center.vue';

const api = vi.hoisted(() => ({
  getNotificationsApi: vi.fn(),
  getNotificationUnreadCountApi: vi.fn(),
  markAllNotificationsReadApi: vi.fn(),
  markNotificationReadApi: vi.fn(),
}));
const router = vi.hoisted(() => ({ push: vi.fn() }));

vi.mock('#/api', () => api);
vi.mock('vue-router', () => ({
  useRoute: () => ({ fullPath: '/' }),
  useRouter: () => router,
}));
vi.mock('@vben/icons', () => ({
  Bell: { template: '<span />' },
  MailCheck: { template: '<span />' },
  RotateCw: { template: '<span />' },
}));
vi.mock('ant-design-vue', () => ({
  Badge: {
    props: ['count'],
    template: '<div :data-count="count"><span>{{ count }}</span><slot /></div>',
  },
  Button: { template: '<button><slot /></button>' },
  Drawer: {
    template: '<div><slot name="extra" /><slot /><slot name="footer" /></div>',
  },
  Empty: { template: '<div>暂无通知</div>' },
  message: { success: vi.fn() },
  Pagination: { template: '<div />' },
  Spin: { template: '<div><slot /></div>' },
  Tooltip: { template: '<div><slot /></div>' },
}));

const notification = {
  body: '工单内容已更新',
  created_at: '2026-07-17T01:00:00Z',
  id: 'notification-1',
  notification_type: 'ticket.updated',
  read_at: null,
  target_id: '1',
  target_type: 'ticket',
  target_url: '/tickets/1',
  title: '工单 #1 已更新',
};

describe('notification center', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.getNotificationUnreadCountApi.mockResolvedValue({ count: 1 });
    api.getNotificationsApi.mockResolvedValue({
      items: [notification],
      page: 1,
      page_size: 50,
      total: 1,
    });
    api.markNotificationReadApi.mockResolvedValue({
      ...notification,
      read_at: '2026-07-17T02:00:00Z',
    });
    api.markAllNotificationsReadApi.mockResolvedValue({ count: 0 });
  });

  afterEach(() => {
    document.body.replaceChildren();
  });

  it('loads unread state, marks a notification read, and follows its target', async () => {
    const container = document.createElement('div');
    document.body.append(container);
    const app = createApp(NotificationCenter);
    app.mount(container);

    await vi.waitFor(() =>
      expect(container.querySelector('[data-count="1"]')).not.toBeNull(),
    );

    container.querySelector<HTMLButtonElement>('[aria-label="通知"]')?.click();
    await vi.waitFor(() =>
      expect(api.getNotificationUnreadCountApi).toHaveBeenCalledTimes(2),
    );
    expect(container.textContent).toContain('工单 #1 已更新');

    container.querySelector<HTMLButtonElement>('.notification-item')?.click();
    await vi.waitFor(() =>
      expect(api.markNotificationReadApi).toHaveBeenCalledWith(
        'notification-1',
      ),
    );
    await vi.waitFor(() =>
      expect(router.push).toHaveBeenCalledWith('/tickets/1'),
    );
    app.unmount();
  });

  it('marks all notifications read from the drawer action', async () => {
    const container = document.createElement('div');
    document.body.append(container);
    const app = createApp(NotificationCenter);
    app.mount(container);

    container.querySelector<HTMLButtonElement>('[aria-label="通知"]')?.click();
    await vi.waitFor(() =>
      expect(api.getNotificationUnreadCountApi).toHaveBeenCalledTimes(2),
    );
    const markAllButton = container.querySelector<HTMLButtonElement>(
      '[aria-label="全部已读"]',
    );
    expect(markAllButton).not.toBeNull();
    expect(markAllButton?.disabled).toBe(false);
    markAllButton?.click();

    await vi.waitFor(() =>
      expect(api.markAllNotificationsReadApi).toHaveBeenCalledOnce(),
    );
    app.unmount();
  });
});
