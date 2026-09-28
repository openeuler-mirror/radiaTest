<script lang="ts" setup>
import type { FeishuIdentity } from '#/api';

import { onMounted, reactive, ref } from 'vue';
import { useRoute } from 'vue-router';

import { Page } from '@vben/common-ui';
import { useUserStore } from '@vben/stores';

import {
  Button,
  Card,
  Descriptions,
  DescriptionsItem,
  Input,
  message,
  Modal,
  Space,
  Tag,
} from 'ant-design-vue';

import {
  changeOwnPasswordApi,
  getMyFeishuBindUrlApi,
  getMyFeishuIdentityApi,
} from '#/api';

import {
  buildPasswordChangePayload,
  validatePasswordForm,
} from './password-form';

const userStore = useUserStore();
const route = useRoute();
const loading = ref(false);
const binding = ref(false);
const passwordOpen = ref(false);
const passwordSubmitting = ref(false);
const identity = ref<FeishuIdentity | null>(null);
const passwordForm = reactive({
  confirmPassword: '',
  oldPassword: '',
  password: '',
});

function displayValue(value: null | string | undefined) {
  return value || '-';
}

function formatTime(value: null | string | undefined) {
  if (!value) return '-';
  return new Date(value).toLocaleString();
}

async function loadIdentity() {
  loading.value = true;
  try {
    identity.value = await getMyFeishuIdentityApi();
  } finally {
    loading.value = false;
  }
}

function feishuRedirectUri() {
  return `${window.location.origin}/api/v1/integrations/feishu/oauth/callback`;
}

async function bindFeishu() {
  binding.value = true;
  try {
    const result = await getMyFeishuBindUrlApi(feishuRedirectUri());
    window.location.href = result.authorize_url;
  } finally {
    binding.value = false;
  }
}

function openPasswordModal() {
  passwordForm.oldPassword = '';
  passwordForm.password = '';
  passwordForm.confirmPassword = '';
  passwordOpen.value = true;
}

async function submitPassword() {
  const validationMessage = validatePasswordForm(passwordForm);
  if (validationMessage) {
    message.warning(validationMessage);
    return;
  }

  passwordSubmitting.value = true;
  try {
    await changeOwnPasswordApi(buildPasswordChangePayload(passwordForm));
    passwordOpen.value = false;
    message.success('密码已修改');
  } catch {
    message.error('密码修改失败，请确认旧密码是否正确');
  } finally {
    passwordSubmitting.value = false;
  }
}

function showBindResult() {
  const result = route.query.feishu_bind;
  if (typeof result !== 'string') {
    return;
  }
  switch (result) {
    case 'conflict': {
      message.error('该飞书账号已绑定到其他 radiaTest 用户');
      break;
    }
    case 'denied': {
      message.warning('已取消飞书授权');
      break;
    }
    case 'success': {
      message.success('飞书账号已绑定');
      break;
    }
    default: {
      message.error('飞书绑定失败');
    }
  }
}

onMounted(() => {
  showBindResult();
  void loadIdentity();
});
</script>

<template>
  <Page title="我的账号">
    <div class="grid gap-4 lg:grid-cols-2">
      <Card title="账号信息">
        <template #extra>
          <Button size="small" @click="openPasswordModal">修改密码</Button>
        </template>
        <Descriptions :column="1" size="small">
          <DescriptionsItem label="用户名">
            {{ userStore.userInfo?.username }}
          </DescriptionsItem>
          <DescriptionsItem label="显示名称">
            {{ userStore.userInfo?.realName }}
          </DescriptionsItem>
          <DescriptionsItem label="权限角色">
            {{ userStore.userInfo?.roles?.join(', ') }}
          </DescriptionsItem>
        </Descriptions>
      </Card>

      <Card :loading="loading" title="飞书绑定">
        <template #extra>
          <Button size="small" @click="loadIdentity">刷新</Button>
        </template>
        <Descriptions :column="1" size="small">
          <DescriptionsItem label="绑定状态">
            <Tag v-if="identity" color="green">已绑定</Tag>
            <Tag v-else>未绑定</Tag>
          </DescriptionsItem>
          <template v-if="identity">
            <DescriptionsItem label="Open ID">
              {{ identity.open_id }}
            </DescriptionsItem>
            <DescriptionsItem label="Union ID">
              {{ displayValue(identity.union_id) }}
            </DescriptionsItem>
            <DescriptionsItem label="绑定时间">
              {{ formatTime(identity.created_at) }}
            </DescriptionsItem>
          </template>
          <DescriptionsItem v-else label="说明">
            绑定后可在飞书私聊中使用 radiaTest Bot。
          </DescriptionsItem>
        </Descriptions>
        <Space v-if="!identity" class="mt-3">
          <Button :loading="binding" type="primary" @click="bindFeishu">
            绑定飞书
          </Button>
        </Space>
      </Card>
    </div>

    <Modal
      v-model:open="passwordOpen"
      :confirm-loading="passwordSubmitting"
      destroy-on-close
      title="修改密码"
      @ok="submitPassword"
    >
      <div class="space-y-3">
        <div>
          <span class="management-filter__label">旧密码</span>
          <Input
            v-model:value="passwordForm.oldPassword"
            autocomplete="current-password"
            type="password"
          />
        </div>
        <div>
          <span class="management-filter__label">新密码</span>
          <Input
            v-model:value="passwordForm.password"
            autocomplete="new-password"
            type="password"
          />
        </div>
        <div>
          <span class="management-filter__label">确认新密码</span>
          <Input
            v-model:value="passwordForm.confirmPassword"
            autocomplete="new-password"
            type="password"
          />
        </div>
      </div>
    </Modal>
  </Page>
</template>
