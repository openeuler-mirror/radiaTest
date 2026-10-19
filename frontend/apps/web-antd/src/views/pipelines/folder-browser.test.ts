/*
 * Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
 * This project is licensed under the Mulan PSL v2.
 * You can use it according to the terms and conditions of the Mulan PSL v2.
 * http://license.coscl.org.cn/MulanPSL2
 */

import { createApp } from 'vue';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import FolderBrowser from './folder-browser.vue';

const api = vi.hoisted(() => ({
  downloadFolderFileApi: vi.fn(),
  listFolderFilesApi: vi.fn(),
  readFolderFileApi: vi.fn(),
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
  Input: { template: '<input />' },
  Spin: { template: '<div><slot /></div>' },
  Tag: { template: '<span><slot /></span>' },
}));

describe('folder log browser', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    const content = Array.from(
      { length: 10_000 },
      (_, index) => `line ${index + 1}`,
    ).join('\n');
    api.listFolderFilesApi.mockResolvedValue({ files: ['logs/ltp.log'] });
    api.readFolderFileApi.mockResolvedValue({ content });
  });

  afterEach(() => {
    document.body.replaceChildren();
  });

  it('renders only a window of a selected large log file', async () => {
    const container = document.createElement('div');
    document.body.append(container);
    const app = createApp(FolderBrowser);

    app.mount(container);
    await vi.waitFor(() => expect(container.textContent).toContain('ltp.log'));
    const fileButton = [...container.querySelectorAll('button')].find(
      (button) => button.textContent?.includes('ltp.log'),
    );
    fileButton?.click();

    await vi.waitFor(() => expect(container.textContent).toContain('line 1'));
    expect(container.textContent).not.toContain('line 10000');
    expect(container.querySelectorAll('*').length).toBeLessThanOrEqual(200);
    app.unmount();
  });
});
