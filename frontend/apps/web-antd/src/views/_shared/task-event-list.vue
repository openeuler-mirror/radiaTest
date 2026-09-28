<script lang="ts" setup>
import type { TaskEventRecord } from '#/api';

import { RotateCw } from '@vben/icons';

import { Button, Tag } from 'ant-design-vue';

defineProps<{
  events: TaskEventRecord[];
  loading?: boolean;
  showRefresh?: boolean;
}>();

defineEmits<{ refresh: [] }>();

function levelColor(level: string) {
  if (level === 'error') return 'red';
  if (level === 'warning') return 'orange';
  return 'blue';
}

function formatTime(value: string) {
  return new Date(value).toLocaleString('zh-CN', { hour12: false });
}

function formatMessage(value: string) {
  return value.replaceAll(String.raw`\n`, '\n');
}
</script>

<template>
  <div class="space-y-3">
    <div v-if="events.length === 0" class="text-sm text-muted-foreground">
      暂无任务事件
    </div>
    <div v-else class="space-y-3">
      <div
        v-for="event in events"
        :key="event.id"
        class="rounded border border-border p-3"
      >
        <div class="mb-2 grid gap-1">
          <div class="flex min-w-0 flex-wrap items-center gap-2">
            <Tag :color="levelColor(event.level)">{{ event.level }}</Tag>
            <span class="min-w-0 text-sm font-medium break-words">
              {{ event.phase }}
            </span>
          </div>
          <span class="text-xs leading-5 text-muted-foreground">
            {{ formatTime(event.created_at) }}
          </span>
        </div>
        <div class="whitespace-pre-wrap break-words text-sm">
          {{ formatMessage(event.message) }}
        </div>
        <div
          v-if="event.host_ip || event.error_code"
          class="mt-2 text-xs text-muted-foreground"
        >
          <span v-if="event.host_ip">宿主 {{ event.host_ip }}</span>
          <span v-if="event.host_ip && event.error_code"> / </span>
          <span v-if="event.error_code">错误码 {{ event.error_code }}</span>
        </div>
      </div>
    </div>
    <div v-if="showRefresh !== false" class="flex justify-end pt-1">
      <Button :loading="loading" size="small" @click="$emit('refresh')">
        <template #icon><RotateCw class="size-4" /></template>
        刷新事件
      </Button>
    </div>
  </div>
</template>
