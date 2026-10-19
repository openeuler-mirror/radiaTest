<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

<script lang="ts" setup>
import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';
import { ArrowLeft, Download, RotateCw } from '@vben/icons';

import { Button, Card, Input, Spin, Tag } from 'ant-design-vue';

import {
  downloadFolderFileApi,
  listFolderFilesApi,
  readFolderFileApi,
} from '#/api';

import VirtualLogViewer from './virtual-log-viewer.vue';

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const files = ref<string[]>([]);
const selectedFile = ref<null | string>(null);
const fileContent = ref('');
const truncated = ref(false);
const search = ref('');

const MAX_DISPLAY = 1024 * 1024;

const filteredFiles = computed(() => {
  if (!search.value) return files.value;
  const q = search.value.toLowerCase();
  return files.value.filter((f) => f.toLowerCase().includes(q));
});

const displayContent = computed(() =>
  fileContent.value.length <= MAX_DISPLAY
    ? fileContent.value
    : fileContent.value.slice(0, MAX_DISPLAY),
);

async function loadFiles() {
  const runId = route.params.runId as string;
  const artifactId = route.params.artifactId as string;
  loading.value = true;
  try {
    const res = await listFolderFilesApi(runId, artifactId);
    files.value = res.files ?? [];
  } finally {
    loading.value = false;
  }
}

async function openFile(filePath: string) {
  const runId = route.params.runId as string;
  const artifactId = route.params.artifactId as string;
  loading.value = true;
  selectedFile.value = filePath;
  try {
    const res = await readFolderFileApi(runId, artifactId, filePath);
    fileContent.value = res.content ?? '';
    truncated.value = fileContent.value.length > MAX_DISPLAY;
  } finally {
    loading.value = false;
  }
}

function closeFile() {
  selectedFile.value = null;
  fileContent.value = '';
}

async function handleDownload() {
  const runId = route.params.runId as string;
  const artifactId = route.params.artifactId as string;
  if (!selectedFile.value) return;
  try {
    const blob = await downloadFolderFileApi(
      runId,
      artifactId,
      selectedFile.value,
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = selectedFile.value.split('/').pop() || 'file';
    document.body.append(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  } catch {
    // best-effort: download failed
  }
}

async function refresh() {
  await (selectedFile.value ? openFile(selectedFile.value) : loadFiles());
}

onMounted(() => {
  void loadFiles();
});
</script>

<template>
  <Page title="文件夹浏览">
    <div class="space-y-3">
      <div class="flex items-center gap-3">
        <Button size="small" @click="router.back()">
          <template #icon><ArrowLeft class="size-4" /></template>
          返回
        </Button>
        <Button :loading="loading" size="small" @click="refresh">
          <template #icon><RotateCw class="size-4" /></template>
          刷新
        </Button>
      </div>

      <Card v-if="!selectedFile" :body-style="{ padding: 0 }">
        <Spin :spinning="loading">
          <div class="p-4">
            <Input
              v-model:value="search"
              allow-clear
              placeholder="搜索文件名..."
              style="margin-bottom: 12px"
            />
            <div class="file-list">
              <Button
                v-for="file in filteredFiles"
                :key="file"
                size="small"
                type="link"
                style="padding: 2px 0; text-align: left"
                @click="openFile(file)"
              >
                {{ file }}
              </Button>
            </div>
            <div
              v-if="filteredFiles.length === 0"
              class="text-center py-4 text-gray-400"
            >
              无文件
            </div>
          </div>
        </Spin>
      </Card>

      <div v-else>
        <div class="flex items-center gap-3 mb-3">
          <Button size="small" @click="closeFile">返回文件列表</Button>
          <Button size="small" type="primary" @click="handleDownload">
            <template #icon><Download class="size-4" /></template>
            下载
          </Button>
          <span class="text-sm text-gray-500">{{ selectedFile }}</span>
          <Tag v-if="truncated" color="orange"> 仅显示前 1MB </Tag>
        </div>
        <Card :body-style="{ padding: 0 }">
          <Spin :spinning="loading">
            <VirtualLogViewer :content="displayContent" />
          </Spin>
        </Card>
      </div>
    </div>
  </Page>
</template>

<style scoped>
.file-list {
  display: flex;
  flex-direction: column;
  gap: 2px;
  max-height: 60vh;
  overflow: auto;
}
</style>
