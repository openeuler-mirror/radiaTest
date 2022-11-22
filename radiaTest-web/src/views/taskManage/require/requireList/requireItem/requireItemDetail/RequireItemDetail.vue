<template>
  <n-card class="card">
    <template #header>
      {{ item.title }}
    </template>
    <template #header-extra>
      <n-icon
        class="button"
        :size="24" 
        @click="() => { emit('close'); }"
      >
        <Close />
      </n-icon>
    </template>
    <n-tabs>
      <n-tab-pane tab="需求详情" name="description">
        <detail-content :require-item="props.item"/>
      </n-tab-pane>
      <n-tab-pane tab="需求进展" name="work-progress">
        <require-progress :require-item="props.item"/>
      </n-tab-pane>
      <n-tab-pane tab="验收进展" name="validate-progress">
        <validate-progress :require-item="props.item"/>
      </n-tab-pane>
    </n-tabs>
  </n-card>
</template>

<script setup>
import DetailContent from './detailContent/DetailContent';
import RequireProgress from './requireProgress/RequireProgress';
import ValidateProgress from './validateProgress/ValidateProgress';
import { Close } from '@vicons/ionicons5';

const props = defineProps({
  item: {
    type: Object,
    default: () => {}
  },
});
const emit = defineEmits(['close']);
</script>

<style scoped lang="less">
.card {
  width: 80%;
  .content-container {
    margin-bottom: 24px;
    display: block;
  }
}
.button:hover {
  cursor: pointer;
}
</style>
