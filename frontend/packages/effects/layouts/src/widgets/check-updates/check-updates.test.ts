import { createApp, defineComponent } from 'vue';

import { afterEach, describe, expect, it, vi } from 'vitest';

import CheckUpdates from './check-updates.vue';

vi.mock('@vben-core/popup-ui', () => ({
  useVbenModal: () => [
    defineComponent({
      template: '<div><slot /><slot name="footer" /></div>',
    }),
    { open: vi.fn() },
  ],
}));

describe('check updates', () => {
  afterEach(() => {
    document.body.replaceChildren();
  });

  it('renders a refresh button without starting a polling timer', () => {
    const intervalSpy = vi.spyOn(globalThis, 'setInterval');
    const container = document.createElement('div');
    document.body.append(container);
    const app = createApp(CheckUpdates);

    app.mount(container);

    expect(container.querySelector('[data-update-refresh]')).not.toBeNull();
    expect(intervalSpy).not.toHaveBeenCalled();
    app.unmount();
    intervalSpy.mockRestore();
  });
});
