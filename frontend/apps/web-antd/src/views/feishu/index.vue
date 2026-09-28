<script lang="ts" setup>
import type { FeishuAppConfig } from '#/api';

import { onMounted, reactive, ref } from 'vue';

import { Page } from '@vben/common-ui';

import {
  Switch as AntSwitch,
  Button,
  Card,
  Descriptions,
  DescriptionsItem,
  Form,
  FormItem,
  Input,
  message,
  Space,
  Tag,
} from 'ant-design-vue';

import { getFeishuAppConfigApi, upsertFeishuAppConfigApi } from '#/api';

interface ValidatableForm {
  validate: () => Promise<void>;
}

const loading = ref(false);
const saving = ref(false);
const formRef = ref<null | ValidatableForm>(null);
const config = ref<FeishuAppConfig | null>(null);

const form = reactive({
  app_id: '',
  app_secret: '',
  is_enabled: true,
});

function formatTime(value: null | string | undefined) {
  if (!value) return '-';
  return new Date(value).toLocaleString();
}

function resetFormFromConfig() {
  form.app_id = config.value?.app_id ?? '';
  form.app_secret = '';
  form.is_enabled = config.value?.is_enabled ?? true;
}

async function loadConfig() {
  loading.value = true;
  try {
    config.value = await getFeishuAppConfigApi();
    resetFormFromConfig();
  } finally {
    loading.value = false;
  }
}

async function submitConfig() {
  await formRef.value?.validate();
  saving.value = true;
  try {
    config.value = await upsertFeishuAppConfigApi({
      app_id: form.app_id,
      app_secret: form.app_secret,
      is_enabled: form.is_enabled,
    });
    resetFormFromConfig();
    message.success('飞书应用配置已保存');
  } finally {
    saving.value = false;
  }
}

onMounted(() => {
  void loadConfig();
});
</script>

<template>
  <Page title="飞书集成">
    <div class="space-y-4">
      <Card :loading="loading" title="当前配置">
        <Descriptions :column="1" size="small">
          <DescriptionsItem label="环境">
            {{ config?.environment || '-' }}
          </DescriptionsItem>
          <DescriptionsItem label="App ID">
            {{ config?.app_id || '-' }}
          </DescriptionsItem>
          <DescriptionsItem label="状态">
            <Tag v-if="config?.is_enabled" color="green">启用</Tag>
            <Tag v-else>未启用</Tag>
          </DescriptionsItem>
          <DescriptionsItem label="App Secret">
            <Tag v-if="config?.has_app_secret" color="blue">已保存</Tag>
            <Tag v-else>未保存</Tag>
          </DescriptionsItem>
          <DescriptionsItem label="更新时间">
            {{ formatTime(config?.updated_at) }}
          </DescriptionsItem>
        </Descriptions>
      </Card>

      <Card title="手动配置飞书应用">
        <Form ref="formRef" :model="form" layout="vertical">
          <div class="management-edit-grid">
            <FormItem
              label="App ID"
              name="app_id"
              :rules="[{ required: true, message: '请输入 App ID' }]"
            >
              <Input v-model:value="form.app_id" allow-clear />
            </FormItem>
            <FormItem
              label="App Secret"
              name="app_secret"
              :rules="[{ required: true, message: '请输入 App Secret' }]"
            >
              <Input
                v-model:value="form.app_secret"
                allow-clear
                placeholder="保存时必须重新输入"
                type="password"
              />
            </FormItem>
            <FormItem label="启用 Bot" name="is_enabled">
              <AntSwitch v-model:checked="form.is_enabled" />
            </FormItem>
          </div>
          <Space>
            <Button :loading="saving" type="primary" @click="submitConfig">
              保存配置
            </Button>
            <Button @click="loadConfig">重置</Button>
          </Space>
        </Form>
      </Card>
    </div>
  </Page>
</template>
