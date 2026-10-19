<!--
  Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
  This project is licensed under the Mulan PSL v2.
  You can use it according to the terms and conditions of the Mulan PSL v2.
  http://license.coscl.org.cn/MulanPSL2
-->

<script lang="ts" setup>
import { computed, watch } from 'vue';

import { useVirtualList } from '@vueuse/core';

const props = defineProps<{ content: string }>();

const lines = computed(() => props.content.split('\n'));
const { containerProps, list, scrollTo, wrapperProps } = useVirtualList(lines, {
  itemHeight: 18,
  overscan: 10,
});

watch(
  () => props.content,
  () => scrollTo(0),
  { flush: 'post' },
);
</script>

<template>
  <div v-bind="containerProps" class="virtual-log-viewer">
    <div v-bind="wrapperProps">
      <div
        v-for="line in list"
        :key="line.index"
        class="virtual-log-viewer__row"
      >
        <span class="virtual-log-viewer__line-number">
          {{ line.index + 1 }}
        </span>
        <span class="virtual-log-viewer__content">{{ line.data }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.virtual-log-viewer {
  max-height: 70vh;
  overflow: auto;
  font-family: Menlo, Monaco, 'Courier New', monospace;
  font-size: 12px;
  line-height: 18px;
  background: hsl(var(--muted));
}

.virtual-log-viewer__row {
  display: flex;
  min-width: max-content;
  height: 18px;
}

.virtual-log-viewer__line-number {
  position: sticky;
  left: 0;
  flex: 0 0 auto;
  min-width: 48px;
  padding: 0 8px 0 12px;
  color: hsl(var(--muted-foreground));
  text-align: right;
  user-select: none;
  background: hsl(var(--accent));
  border-right: 1px solid hsl(var(--border));
}

.virtual-log-viewer__content {
  padding: 0 12px;
  tab-size: 4;
  white-space: pre;
}
</style>
