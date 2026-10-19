<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

<script lang="ts" setup>
import type { CaseMugenLog, PipelineTestCaseRunRecord } from '#/api';

import { computed, onMounted, ref } from 'vue';
import { useRoute, useRouter } from 'vue-router';

import { Page } from '@vben/common-ui';
import { ArrowLeft, Download, RotateCw } from '@vben/icons';

import { Button, Card, Spin, Tag } from 'ant-design-vue';

import {
  downloadFolderFileApi,
  getCaseMugenLogApi,
  getRunJobDetailApi,
  readFolderFileApi,
} from '#/api';

import VirtualLogViewer from './virtual-log-viewer.vue';

const route = useRoute();
const router = useRouter();
const loading = ref(false);
const data = ref<CaseMugenLog | null>(null);
const caseRun = ref<null | PipelineTestCaseRunRecord>(null);
const selectedFile = ref('');
const fileContent = ref('');
const truncated = ref(false);

const MAX_DISPLAY = 1024 * 1024;

const displayContent = computed(() => {
  if (fileContent.value.length <= MAX_DISPLAY) return fileContent.value;
  return fileContent.value.slice(0, MAX_DISPLAY);
});

async function loadLog() {
  const runJobId = route.params.id as string;
  const caseRunId = route.params.caseRunId as string;
  loading.value = true;
  try {
    const [mugenLog, runJobDetail] = await Promise.all([
      getCaseMugenLogApi(runJobId, caseRunId).catch(() => null),
      getRunJobDetailApi(runJobId),
    ]);
    data.value = mugenLog;
    if (mugenLog) {
      selectedFile.value = mugenLog.file_path;
      fileContent.value = mugenLog.content;
      truncated.value = mugenLog.content.length > MAX_DISPLAY;
    }
    caseRun.value =
      runJobDetail.case_runs?.find((cr) => cr.id === caseRunId) ?? null;
  } finally {
    loading.value = false;
  }
}

async function switchFile(filePath: string) {
  if (!data.value || filePath === selectedFile.value) return;
  const prevFile = selectedFile.value;
  loading.value = true;
  selectedFile.value = filePath;
  try {
    const res = await readFolderFileApi(
      data.value.run_id,
      data.value.artifact_id,
      filePath,
    );
    fileContent.value = res.content;
    truncated.value = res.content.length > MAX_DISPLAY;
  } catch {
    selectedFile.value = prevFile;
  } finally {
    loading.value = false;
  }
}

async function handleDownload() {
  if (!data.value) return;
  try {
    const blob = await downloadFolderFileApi(
      data.value.run_id,
      data.value.artifact_id,
      selectedFile.value,
    );
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = selectedFile.value.split('/').pop() || 'mugen.log';
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

onMounted(() => {
  void loadLog();
});
</script>

<template>
  <Page title="Mugen 日志">
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
        <Button v-if="data" size="small" type="primary" @click="handleDownload">
          <template #icon><Download class="size-4" /></template>
          下载
        </Button>
        <Tag v-if="truncated" color="orange">仅显示前 1MB，下载看全文</Tag>
      </div>

      <!-- stdout / stderr (from case_run) -->
      <Card v-if="caseRun" :body-style="{ padding: '12px 16px' }">
        <div
          v-if="caseRun.suite_name || caseRun.case_name"
          class="mb-2 flex items-center gap-2"
        >
          <Tag color="blue">{{ caseRun.status }}</Tag>
          <span class="text-sm font-semibold">
            {{ caseRun.suite_name }}/{{ caseRun.case_name }}
          </span>
          <span
            v-if="caseRun.exit_code !== null"
            class="text-xs"
            style="color: hsl(var(--muted-foreground))"
          >
            exit={{ caseRun.exit_code }}
          </span>
        </div>
        <div v-if="caseRun.stdout_summary" class="mb-2">
          <div class="output-label">stdout:</div>
          <pre class="output-pre">{{ caseRun.stdout_summary }}</pre>
        </div>
        <div v-if="caseRun.stderr_summary">
          <div class="output-label">stderr:</div>
          <pre class="output-pre">{{ caseRun.stderr_summary }}</pre>
        </div>
      </Card>

      <!-- mugen log file selector -->
      <Card
        v-if="data && data.files.length > 1"
        :body-style="{ padding: '8px 16px' }"
      >
        <div class="flex flex-wrap gap-2">
          <Button
            v-for="file in data.files"
            :key="file"
            size="small"
            :type="file === selectedFile ? 'primary' : 'link'"
            style="padding: 0"
            @click="switchFile(file)"
          >
            {{ file.split('/').pop() }}
          </Button>
        </div>
      </Card>

      <!-- mugen log file viewer -->
      <Card :body-style="{ padding: 0 }">
        <Spin :spinning="loading">
          <VirtualLogViewer v-if="data" :content="displayContent" />
          <div
            v-else-if="!loading"
            class="text-center py-8"
            style="color: hsl(var(--muted-foreground))"
          >
            无 mugen 日志
          </div>
        </Spin>
      </Card>
    </div>
  </Page>
</template>

<style scoped>
.output-label {
  font-size: 11px;
  color: hsl(var(--muted-foreground));
}

.output-pre {
  max-height: 300px;
  padding: 4px 8px;
  margin: 4px 0;
  overflow: auto;
  font-size: 11px;
  line-height: 1.5;
  color: hsl(var(--card-foreground));
  word-break: break-all;
  white-space: pre-wrap;
  background: hsl(var(--muted));
  border: 1px solid hsl(var(--border));
  border-radius: 4px;
}
</style>
