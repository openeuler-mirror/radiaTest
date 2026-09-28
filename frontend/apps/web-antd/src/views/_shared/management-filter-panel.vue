<script lang="ts" setup>
import { RotateCw, Search } from '@vben/icons';

import { Button, Card, Tag } from 'ant-design-vue';

withDefaults(
  defineProps<{
    activeFilterCount?: number;
    loading?: boolean;
  }>(),
  {
    activeFilterCount: 0,
    loading: false,
  },
);

defineEmits<{
  reset: [];
  search: [];
}>();
</script>

<template>
  <Card :body-style="{ padding: '16px' }">
    <div class="management-filter">
      <slot></slot>
      <div class="management-filter__actions">
        <slot name="extra"></slot>
        <Tag v-if="activeFilterCount" color="blue">
          {{ activeFilterCount }} 个筛选
        </Tag>
        <Button
          :loading="loading"
          size="small"
          type="primary"
          @click="$emit('search')"
        >
          <template #icon><Search class="size-4" /></template>
          查询
        </Button>
        <Button size="small" @click="$emit('reset')">
          <template #icon><RotateCw class="size-4" /></template>
          重置
        </Button>
      </div>
    </div>
  </Card>
</template>
