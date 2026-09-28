<script lang="ts" setup>
import type RFB from '@novnc/novnc';

import type { VMConsoleRecord } from '#/api';

import {
  computed,
  onActivated,
  onBeforeUnmount,
  onDeactivated,
  onMounted,
  ref,
} from 'vue';
import { useRoute } from 'vue-router';

import { Page } from '@vben/common-ui';
import { useTabs } from '@vben/hooks';
import { CornerDownLeft, Maximize, RotateCw } from '@vben/icons';

import NoVNCRFB from '@novnc/novnc';
import { Button, Card, message, Select, Space, Tag } from 'ant-design-vue';

import { getVMConsoleApi, getVMPowerApi } from '#/api';

import { buildCtrlAltKeySequence, ctrlAltTargets } from './console-keys';
import { buildVNCOptions } from './console-options';
import { disconnectedConsoleStatus } from './console-status';
import { vmConsoleConfigTitle } from './vm-view';

type ConsoleStatus =
  | 'connected'
  | 'connecting'
  | 'destroyed'
  | 'disconnected'
  | 'failed'
  | 'loading'
  | 'stopped';

const route = useRoute();
const { setTabTitle } = useTabs();
const resourceId = computed(() => String(route.params.resourceId ?? ''));
const shellRef = ref<HTMLElement | null>(null);
const screenRef = ref<HTMLElement | null>(null);
const config = ref<null | VMConsoleRecord>(null);
const status = ref<ConsoleStatus>('loading');
const errorMessage = ref('');
const selectedCtrlAltTarget = ref('F2');
let rfb: null | RFB = null;
let reconnectOnActivation = false;

const routeTabTitle = computed(() =>
  typeof route.query.tabTitle === 'string' ? route.query.tabTitle : 'VM 控制台',
);
const consoleTitle = computed(() =>
  vmConsoleConfigTitle(config.value, routeTabTitle.value),
);

const statusMeta = computed(() => {
  const map: Record<ConsoleStatus, { color: string; label: string }> = {
    connected: { color: 'green', label: '已连接' },
    connecting: { color: 'blue', label: '连接中' },
    destroyed: { color: 'default', label: '已销毁' },
    disconnected: { color: 'default', label: '已断开' },
    failed: { color: 'red', label: '连接失败' },
    loading: { color: 'blue', label: '加载中' },
    stopped: { color: 'default', label: '已关机' },
  };
  return map[status.value];
});
const canSendKeys = computed(
  () => status.value === 'connected' && Boolean(rfb),
);

function disconnect() {
  const currentRfb = rfb;
  rfb = null;
  currentRfb?.disconnect();
}

async function loadDisconnectedStatus() {
  try {
    const power = await getVMPowerApi(resourceId.value);
    return disconnectedConsoleStatus(power.power_state);
  } catch {
    return null;
  }
}

async function connectConsole() {
  disconnect();
  status.value = 'loading';
  errorMessage.value = '';
  try {
    const power = await getVMPowerApi(resourceId.value);
    const unavailableStatus = disconnectedConsoleStatus(power.power_state);
    if (unavailableStatus !== 'disconnected') {
      status.value = unavailableStatus;
      return;
    }
    const consoleConfig = await getVMConsoleApi(resourceId.value);
    config.value = consoleConfig;
    void setTabTitle(consoleTitle.value);
    if (!screenRef.value) {
      throw new Error('控制台容器未初始化');
    }
    screenRef.value.replaceChildren();
    status.value = 'connecting';
    const nextRfb = new NoVNCRFB(
      screenRef.value,
      consoleConfig.url,
      buildVNCOptions(consoleConfig),
    );
    rfb = nextRfb;
    nextRfb.scaleViewport = true;
    nextRfb.resizeSession = false;
    nextRfb.clipViewport = true;
    nextRfb.focusOnClick = true;
    nextRfb.viewOnly = false;
    nextRfb.addEventListener('connect', () => {
      if (rfb !== nextRfb) return;
      status.value = 'connected';
      rfb?.focus();
    });
    nextRfb.addEventListener('disconnect', (event) => {
      if (rfb !== nextRfb) return;
      const detail = (event as CustomEvent<{ clean: boolean }>).detail;
      status.value = detail.clean ? 'disconnected' : 'failed';
      if (!detail.clean) {
        errorMessage.value = '控制台连接异常断开';
      }
      void loadDisconnectedStatus().then((nextStatus) => {
        if (rfb !== nextRfb) return;
        status.value = nextStatus ?? 'disconnected';
        if (status.value !== 'disconnected') errorMessage.value = '';
      });
    });
    nextRfb.addEventListener('credentialsrequired', () => {
      if (rfb !== nextRfb) return;
      status.value = 'failed';
      errorMessage.value = 'VNC 需要密码，但当前 VM 未配置控制台密码';
    });
    nextRfb.addEventListener('securityfailure', (event) => {
      if (rfb !== nextRfb) return;
      const detail = (event as CustomEvent<{ reason?: string }>).detail;
      status.value = 'failed';
      errorMessage.value = detail.reason || 'VNC 安全协商失败';
    });
  } catch (error) {
    status.value = 'failed';
    errorMessage.value =
      error instanceof Error ? error.message : '控制台连接失败';
    message.error(errorMessage.value);
  }
}

async function enterFullscreen() {
  try {
    await shellRef.value?.requestFullscreen();
  } catch {
    message.error('无法进入全屏');
  }
}

function sendCtrlAltTarget() {
  if (!rfb) return;
  const sequence = buildCtrlAltKeySequence(selectedCtrlAltTarget.value);
  if (!sequence) return;
  for (const key of sequence) {
    rfb.sendKey(key.keysym, key.code, key.down);
  }
  rfb.focus();
}

onMounted(() => {
  void setTabTitle(consoleTitle.value);
  void connectConsole();
});

onDeactivated(() => {
  reconnectOnActivation = true;
  disconnect();
  status.value = 'disconnected';
  errorMessage.value = '';
});

onActivated(() => {
  if (!reconnectOnActivation) return;
  reconnectOnActivation = false;
  void connectConsole();
});

onBeforeUnmount(() => {
  reconnectOnActivation = false;
  disconnect();
});
</script>

<template>
  <Page :title="consoleTitle">
    <div ref="shellRef" class="vm-console-shell">
      <Card :body-style="{ padding: '16px' }">
        <div class="flex flex-wrap items-center justify-between gap-3">
          <Space wrap>
            <Tag :color="statusMeta.color">{{ statusMeta.label }}</Tag>
            <span>{{ config?.vm_name || resourceId }}</span>
            <span v-if="config" class="text-gray-500">
              {{ config.url }}
            </span>
          </Space>
          <Space wrap>
            <Tag>Ctrl</Tag>
            <Tag>Alt</Tag>
            <Select
              v-model:value="selectedCtrlAltTarget"
              :options="ctrlAltTargets"
              class="w-24"
            />
            <Button :disabled="!canSendKeys" @click="sendCtrlAltTarget">
              <template #icon>
                <CornerDownLeft class="size-4" />
              </template>
              发送键
            </Button>
            <Button @click="enterFullscreen">
              <template #icon>
                <Maximize class="size-4" />
              </template>
              全屏
            </Button>
            <Button
              :disabled="status === 'destroyed'"
              :loading="status === 'loading'"
              @click="connectConsole"
            >
              <template #icon>
                <RotateCw class="size-4" />
              </template>
              重连
            </Button>
          </Space>
        </div>
      </Card>

      <div class="vm-console-screen">
        <div ref="screenRef" class="vm-console-target"></div>
        <div
          v-if="status === 'loading' || status === 'failed'"
          class="vm-console-overlay"
        >
          <div class="vm-console-overlay-text">
            {{ status === 'loading' ? '正在加载控制台配置...' : errorMessage }}
          </div>
        </div>
      </div>
    </div>
  </Page>
</template>

<style scoped>
.vm-console-shell {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.vm-console-screen {
  position: relative;
  height: calc(100vh - 240px);
  min-height: 480px;
  overflow: hidden;
  background: #111;
  border: 1px solid rgb(45 45 48);
  border-radius: 8px;
}

.vm-console-target {
  width: 100%;
  height: 100%;
}

.vm-console-overlay {
  position: absolute;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  pointer-events: none;
  background: rgb(0 0 0 / 60%);
}

.vm-console-overlay-text {
  max-width: 640px;
  color: #fff;
  text-align: center;
  overflow-wrap: anywhere;
}

.vm-console-shell:fullscreen {
  padding: 16px;
  background: #111;
}

.vm-console-shell:fullscreen .vm-console-screen {
  height: calc(100vh - 88px);
}
</style>
