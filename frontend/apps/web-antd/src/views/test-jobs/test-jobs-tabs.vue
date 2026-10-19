<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

<script lang="ts" setup>
import { computed } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { TabPane, Tabs } from 'ant-design-vue';

const route = useRoute();
const router = useRouter();
const activeKey = computed(() =>
  route.path.startsWith('/test-jobs/templates') ? 'templates' : 'list',
);

function changeTab(key: number | string) {
  void router.push(
    key === 'templates' ? '/test-jobs/templates' : '/test-jobs/list',
  );
}
</script>

<template>
  <Tabs :active-key="activeKey" @change="changeTab">
    <TabPane key="list" tab="任务列表" />
    <TabPane key="templates" tab="任务模板" />
  </Tabs>
</template>
