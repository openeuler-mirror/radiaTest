/*
 * Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
 * This project is licensed under the Mulan PSL v2.
 * You can use it according to the terms and conditions of the Mulan PSL v2.
 * http://license.coscl.org.cn/MulanPSL2
 */

import { createApp, h, nextTick, ref } from 'vue';

import { afterEach, describe, expect, it } from 'vitest';

import VirtualLogViewer from './virtual-log-viewer.vue';

describe('virtual log viewer', () => {
  afterEach(() => {
    document.body.replaceChildren();
  });

  it('renders only the visible window for a large log', async () => {
    const container = document.createElement('div');
    document.body.append(container);
    const content = Array.from(
      { length: 10_000 },
      (_, index) => `line ${index + 1}`,
    ).join('\n');
    const app = createApp({
      render: () => h(VirtualLogViewer, { content }),
    });

    app.mount(container);
    await nextTick();

    const rows = container.querySelectorAll('.virtual-log-viewer__row');
    expect(rows.length).toBeGreaterThan(0);
    expect(rows.length).toBeLessThanOrEqual(50);
    expect(rows[0]?.textContent).toContain('line 1');
    expect(container.textContent).not.toContain('line 10000');
    app.unmount();
  });

  it('returns to the first line when the log content changes', async () => {
    const container = document.createElement('div');
    document.body.append(container);
    const content = ref(
      Array.from({ length: 2000 }, (_, index) => `line ${index + 1}`).join(
        '\n',
      ),
    );
    const app = createApp({
      render: () => h(VirtualLogViewer, { content: content.value }),
    });

    app.mount(container);
    await nextTick();
    const viewer = container.querySelector<HTMLElement>('.virtual-log-viewer');
    expect(viewer).not.toBeNull();
    Object.defineProperty(viewer, 'clientHeight', { value: 180 });
    if (viewer) {
      viewer.scrollTop = 999 * 18;
      viewer.dispatchEvent(new Event('scroll'));
    }
    await nextTick();
    const rows = container.querySelectorAll('.virtual-log-viewer__row');
    const line1000 = [...rows].find((row) =>
      row.textContent?.includes('line 1000'),
    );
    expect(rows.length).toBeLessThanOrEqual(50);
    expect(
      line1000?.querySelector('.virtual-log-viewer__line-number')?.textContent,
    ).toContain('1000');

    content.value = 'new first\nnew second';
    await nextTick();

    expect(viewer?.scrollTop).toBe(0);
    expect(container.textContent).toContain('new first');
    app.unmount();
  });
});
