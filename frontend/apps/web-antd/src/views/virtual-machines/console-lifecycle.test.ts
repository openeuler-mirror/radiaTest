import { createApp, defineComponent, h, KeepAlive, nextTick, ref } from 'vue';

import { afterEach, describe, expect, it, vi } from 'vitest';

import ConsolePage from './console.vue';

const mocks = vi.hoisted(() => ({
  instances: [] as Array<{ disconnect: ReturnType<typeof vi.fn> }>,
}));

vi.mock('@novnc/novnc', () => ({
  default: class {
    clipViewport = false;
    disconnect = vi.fn();
    focus = vi.fn();
    focusOnClick = false;
    resizeSession = false;
    scaleViewport = false;
    viewOnly = false;

    constructor() {
      mocks.instances.push(this);
    }

    addEventListener() {}
  },
}));

vi.mock('@vben/common-ui', () => ({
  Page: { template: '<div><slot /></div>' },
}));
vi.mock('@vben/hooks', () => ({
  useTabs: () => ({ setTabTitle: vi.fn() }),
}));
vi.mock('@vben/icons', () => ({
  CornerDownLeft: { template: '<span />' },
  Maximize: { template: '<span />' },
  RotateCw: { template: '<span />' },
}));
vi.mock('ant-design-vue', () => ({
  Button: { template: '<button><slot /></button>' },
  Card: { template: '<div><slot /></div>' },
  message: { error: vi.fn() },
  Select: { template: '<select />' },
  Space: { template: '<div><slot /></div>' },
  Tag: { template: '<span><slot /></span>' },
}));
vi.mock('vue-router', () => ({
  useRoute: () => ({ params: { resourceId: 'vm-1' }, query: {} }),
}));
vi.mock('#/api', () => ({
  getVMConsoleApi: vi.fn(async () => ({
    password: null,
    port: 5901,
    resource_id: 'vm-1',
    url: 'ws://host:5701/',
    vm_name: 'vm-1',
    websocket_port: 5701,
  })),
  getVMPowerApi: vi.fn(async () => ({
    power_state: 'running',
    resource_id: 'vm-1',
    vm_name: 'vm-1',
  })),
}));

describe('vm console lifecycle', () => {
  afterEach(() => {
    mocks.instances.length = 0;
    document.body.replaceChildren();
  });

  it('disconnects while its tab is inactive and reconnects on activation', async () => {
    const visible = ref(true);
    const root = defineComponent(
      () => () =>
        h(KeepAlive, null, {
          default: () => (visible.value ? h(ConsolePage) : h('div')),
        }),
    );
    const container = document.createElement('div');
    document.body.append(container);
    const app = createApp(root);
    app.mount(container);

    await vi.waitFor(() => expect(mocks.instances).toHaveLength(1));
    visible.value = false;
    await nextTick();
    expect(mocks.instances[0]?.disconnect).toHaveBeenCalledOnce();

    visible.value = true;
    await nextTick();
    await vi.waitFor(() => expect(mocks.instances).toHaveLength(2));
    app.unmount();
  });
});
