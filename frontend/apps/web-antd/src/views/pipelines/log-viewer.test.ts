/*
 * Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
 * This project is licensed under the Mulan PSL v2.
 * You can use it according to the terms and conditions of the Mulan PSL v2.
 * http://license.coscl.org.cn/MulanPSL2
 */

import { createApp } from 'vue';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import LogViewer from './log-viewer.vue';

const api = vi.hoisted(() => ({
  downloadRunLogApi: vi.fn(),
  readRunLogApi: vi.fn(),
}));

vi.mock('#/api', () => api);
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { artifactId: 'artifact-1', runId: 'run-1' } }),
  useRouter: () => ({ back: vi.fn() }),
}));
vi.mock('@vben/common-ui', () => ({
  Page: { template: '<main><slot /></main>' },
}));
vi.mock('@vben/icons', () => ({
  ArrowLeft: { template: '<span />' },
  Download: { template: '<span />' },
  RotateCw: { template: '<span />' },
}));
vi.mock('ant-design-vue', () => ({
  Button: { template: '<button><slot name="icon" /><slot /></button>' },
  Card: { template: '<section><slot /></section>' },
  Spin: { template: '<div><slot /></div>' },
  Tag: { template: '<span><slot /></span>' },
}));

describe('pipeline log viewer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    api.readRunLogApi.mockResolvedValue({ content: 'line 1\nline 2' });
  });

  afterEach(() => {
    document.body.replaceChildren();
  });

  it('loads log content only after the user requests it', async () => {
    const container = document.createElement('div');
    document.body.append(container);
    const app = createApp(LogViewer);

    app.mount(container);

    expect(api.readRunLogApi).not.toHaveBeenCalled();
    const viewButton = [...container.querySelectorAll('button')].find(
      (button) => button.textContent?.includes('查看内容'),
    );
    expect(viewButton).toBeDefined();
    viewButton?.click();

    await vi.waitFor(() =>
      expect(api.readRunLogApi).toHaveBeenCalledWith('run-1', 'artifact-1'),
    );
    await vi.waitFor(() => expect(container.textContent).toContain('line 1'));
    app.unmount();
  });
});
