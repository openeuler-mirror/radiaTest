<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

<script lang="ts" setup>
import { computed, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';
import { ArrowLeft, Download, RotateCw } from '@vben/icons';

import { Button, Card, Spin, Tag } from 'ant-design-vue';

import { downloadRunLogApi, readRunLogApi } from '#/api';

import VirtualLogViewer from './virtual-log-viewer.vue';

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const content = ref('');
const truncated = ref(false);
const contentLoaded = ref(false);

const MAX_DISPLAY = 1024 * 1024;

const displayContent = computed(() => {
  if (content.value.length <= MAX_DISPLAY) return content.value;
  return content.value.slice(0, MAX_DISPLAY);
});

async function loadLog() {
  const runId = route.params.runId as string;
  const artifactId = route.params.artifactId as string;
  loading.value = true;
  try {
    const res = await readRunLogApi(runId, artifactId);
    content.value = res.content ?? '';
    truncated.value = content.value.length > MAX_DISPLAY;
    contentLoaded.value = true;
  } finally {
    loading.value = false;
  }
}

async function handleDownload() {
  const runId = route.params.runId as string;
  const artifactId = route.params.artifactId as string;
  try {
    const blob = await downloadRunLogApi(runId, artifactId);
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = artifactId;
    document.body.append(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch {
    // best-effort: download failed
  }
}

async function refresh() {
  await loadLog();
}
</script>

<template>
  <Page title="日志查看">
    <div class="space-y-3">
      <div class="flex items-center gap-3">
        <Button size="small" @click="router.back()">
          <template #icon><ArrowLeft class="size-4" /></template>
          返回
        </Button>
        <Button
          :disabled="!contentLoaded"
          :loading="loading"
          size="small"
          @click="refresh"
        >
          <template #icon><RotateCw class="size-4" /></template>
          刷新
        </Button>
        <Button size="small" type="primary" @click="handleDownload">
          <template #icon><Download class="size-4" /></template>
          下载
        </Button>
        <Button
          v-if="!contentLoaded"
          :loading="loading"
          size="small"
          @click="loadLog"
        >
          查看内容
        </Button>
        <Tag v-if="truncated" color="orange"> 仅显示前 1MB，下载看全文 </Tag>
      </div>

      <Card v-if="contentLoaded" :body-style="{ padding: 0 }">
        <Spin :spinning="loading">
          <VirtualLogViewer :content="displayContent" />
        </Spin>
      </Card>
      <Card v-else :body-style="{ padding: '32px' }">
        <div style="color: hsl(var(--muted-foreground)); text-align: center">
          点击"查看内容"加载日志，或直接"下载"全文
        </div>
      </Card>
    </div>
  </Page>
</template>
