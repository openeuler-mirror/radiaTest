/*
 * Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
 * This project is licensed under the Mulan PSL v2.
 * You can use it according to the terms and conditions of the Mulan PSL v2.
 * http://license.coscl.org.cn/MulanPSL2
 */

import { createApp } from 'vue';

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import CaseLog from './case-log.vue';

const api = vi.hoisted(() => ({
  downloadFolderFileApi: vi.fn(),
  getCaseMugenLogApi: vi.fn(),
  getRunJobDetailApi: vi.fn(),
  readFolderFileApi: vi.fn(),
}));

vi.mock('#/api', () => api);
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { caseRunId: 'case-1', id: 'job-1' } }),
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

describe('case log page', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    const content = Array.from(
      { length: 10_000 },
      (_, index) => `line ${index + 1}`,
    ).join('\n');
    api.getCaseMugenLogApi.mockResolvedValue({
      artifact_id: 'artifact-1',
      content,
      file_path: 'logs/ltp.log',
      files: ['logs/ltp.log'],
      run_id: 'run-1',
    });
    api.getRunJobDetailApi.mockResolvedValue({ case_runs: [] });
  });

  afterEach(() => {
    document.body.replaceChildren();
  });

  it('renders only a window of a large case log', async () => {
    const container = document.createElement('div');
    document.body.append(container);
    const app = createApp(CaseLog);

    app.mount(container);

    await vi.waitFor(() => expect(container.textContent).toContain('line 1'));
    expect(container.textContent).not.toContain('line 10000');
    expect(container.querySelectorAll('*').length).toBeLessThanOrEqual(200);
    app.unmount();
  });
});
