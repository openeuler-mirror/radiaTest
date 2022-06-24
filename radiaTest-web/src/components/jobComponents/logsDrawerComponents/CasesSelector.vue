<template>
  <n-card class="caseCard" hoverable>
    <div style="width: 100%; margin-bottom: 20px">
      <n-space item-style="display: flex;" align="center" justify="start">
        <n-checkbox v-model:checked="successCheck">成功用例</n-checkbox>
        <n-checkbox v-model:checked="failCheck">失败用例</n-checkbox>
      </n-space>
    </div>
    <div style="width: 100%; margin-bottom: 20px">
      <n-input
        v-model:value="searchCaseValue"
        placeholder="搜索用例"
        size="large"
        clearable
        round
      />
    </div>
    <div v-for="_analyzed in analyzeds" :key="_analyzed.id">
      <n-alert
        class="alertButton"
        :title="_analyzed.case.name"
        :id="'case' + _analyzed.case.id"
        :type="_analyzed.result === 'success' ? 'success' : 'error'"
        @click="handleSelectCase(_analyzed.case.id)"
      >
        <template #header>
          <n-h4 style="word-wrap: break-word">
            {{ _analyzed.case.name }}
          </n-h4>
        </template>
        用时:
      </n-alert>
    </div>
  </n-card>
</template>

<script>
import { defineComponent } from 'vue';

import logsDrawer from '@/views/testCenter/job/modules/logsDrawer.js';

export default defineComponent({
  setup() {
    return {
      ...logsDrawer,
    };
  },
});
</script>

<style scoped>
.caseCard {
  height: 100%;
}
.alertButton {
  box-shadow: 0 4px 36px 0 rgba(190, 196, 204, 0.2);
  margin-bottom: 40px;
}
.alertButton:hover {
  cursor: pointer;
  box-shadow: 0 4px 20px 4px rgba(0, 0, 0, 0.4) !important;
}
</style>
