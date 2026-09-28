import { createApp, h } from 'vue';

import { afterEach, describe, expect, it, vi } from 'vitest';

import ManagementFilterPanel from './management-filter-panel.vue';

vi.mock('@vben/icons', () => ({
  RotateCw: { template: '<span />' },
  Search: { template: '<span />' },
}));

vi.mock('ant-design-vue', () => ({
  Button: { template: '<button><slot /></button>' },
  Card: { template: '<div><slot /></div>' },
  Tag: { template: '<span><slot /></span>' },
}));

describe('management filter panel', () => {
  afterEach(() => {
    document.body.replaceChildren();
  });

  it('renders caller fields and emits the shared actions', async () => {
    const search = vi.fn();
    const reset = vi.fn();
    const container = document.createElement('div');
    document.body.append(container);
    const app = createApp({
      render: () =>
        h(
          ManagementFilterPanel,
          {
            activeFilterCount: 2,
            onReset: reset,
            onSearch: search,
          },
          {
            default: () => h('input', { 'data-testid': 'field' }),
            extra: () => h('span', { 'data-testid': 'extra' }, 'AND'),
          },
        ),
    });
    app.mount(container);

    expect(container.querySelector('[data-testid="field"]')).not.toBeNull();
    expect(container.querySelector('[data-testid="extra"]')?.textContent).toBe(
      'AND',
    );
    expect(container.textContent).toContain('2 个筛选');

    const buttons = [...container.querySelectorAll('button')];
    const actions = container.querySelector('.management-filter__actions');
    expect(buttons.every((button) => button.parentElement === actions)).toBe(
      true,
    );
    buttons.find((button) => button.textContent?.includes('查询'))?.click();
    buttons.find((button) => button.textContent?.includes('重置'))?.click();

    expect(search).toHaveBeenCalledOnce();
    expect(reset).toHaveBeenCalledOnce();
    app.unmount();
  });
});
