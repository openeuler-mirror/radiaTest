<script lang="ts" setup>
import { onMounted, ref } from 'vue';

import { Page } from '@vben/common-ui';
import { useUserStore } from '@vben/stores';

import { Card, Descriptions, DescriptionsItem, Tag } from 'ant-design-vue';

import { getDatabaseHealthApi } from '#/api';

const userStore = useUserStore();
const databaseReachable = ref<boolean | null>(null);

onMounted(async () => {
  try {
    const health = await getDatabaseHealthApi();
    databaseReachable.value =
      health.status === 'ok' && health.database === 'reachable';
  } catch {
    databaseReachable.value = false;
  }
});
</script>

<template>
  <Page title="radiaTest">
    <div class="grid gap-4 lg:grid-cols-2">
      <Card title="当前用户">
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

      <Card title="系统状态">
        <Descriptions :column="1" size="small">
          <DescriptionsItem label="Web 服务">
            <Tag color="green">正常</Tag>
          </DescriptionsItem>
          <DescriptionsItem label="PostgreSQL">
            <Tag v-if="databaseReachable === null">检查中</Tag>
            <Tag v-else-if="databaseReachable" color="green">正常</Tag>
            <Tag v-else color="red">不可用</Tag>
          </DescriptionsItem>
        </Descriptions>
      </Card>
    </div>
  </Page>
</template>
