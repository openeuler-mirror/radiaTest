<template>
  <div v-if="showDetail">
    <div class="details-container">
      <div style="display: flex; justify-content: space-between; margin: 10px 0">
        <n-tabs type="line" @update:value="tabChange" :value="activeTab">
          <n-tab name="details">详情</n-tab>
          <n-tab name="auto" :disabled="!caseInfo.code">自动化脚本</n-tab>
        </n-tabs>
      </div>
      <n-card size="large">
        <n-spin stroke="rgba(0, 47, 167, 1)" :show="loading">
          <template v-if="activeTab === 'details'">
            <collapse-list :list="detailsList" @edit="edit" />
          </template>
          <template v-else-if="activeTab === 'auto'">
            <auto-script :code="caseInfo.code" />
          </template>
          <template v-else>
            <historical-version />
          </template>
        </n-spin>
      </n-card>
    </div>
    <caseModifyForm ref="modifyModal" :formValue="editInfoValue" @submit="editSubmit" />
    <n-modal
      v-model:show="showReportModal"
      preset="dialog"
      :show-icon="false"
      title="Dialog"
      class="previewWindow"
      :style="{ width: previewWidth + 'px', height: previewHeight + 'px' }"
    >
      <template #header>
        <h3>{{ report.name }}</h3>
      </template>
      <div class="previewContent" :style="{ height: previewHeight - 100 + 'px' }">
        <v-md-editor
          v-model="report.content"
          :left-toolbar="tools"
          :right-toolbar="rightTools"
          :include-level="[1, 4]"
          :toolbar="toolbar"
        ></v-md-editor>
      </div>
    </n-modal>
  </div>
  <div
    v-else
    style="height: 100%; width: 100%; display: flex; justify-content: center; align-items: center"
  >
    <n-empty description="开发中..."> </n-empty>
  </div>
</template>
<script>
import { modules } from './modules';
import collapseList from '@/components/collapseList/collapseList.vue';
import autoScript from './tabview/autoScript.vue';

import { ref, provide } from 'vue';
import { formatTime } from '@/assets/utils/dateFormatUtils';
import caseModifyForm from '@/components/testcaseComponents/caseModifyForm.vue';
import { previewWidth, previewHeight } from '@/views/taskManage/task/modules/mdFile';

export default {
  components: {
    collapseList,
    autoScript,
    caseModifyForm,
  },
  mounted() {
    if (this.$route.params.taskId === 'development') {
      this.showDetail = false;
      sessionStorage.setItem('refresh', 0);
    } else {
      this.$nextTick(() => {
        this.getDetail(window.atob(this.$route.params.taskId));
        setTimeout(() => {
          if (Number(sessionStorage.getItem('refresh')) === 1) {
            window.dispatchEvent(
              new CustomEvent('refreshEvent', {
                detail: { caseNodeId: window.atob(this.$route.params.taskId) },
              })
            );
            sessionStorage.setItem('refresh', 0);
          }
        }, 500);
      });
    }
  },
  setup() {
    const showDetail = ref(true);
    provide('caseInfo', modules.caseInfo);
    return {
      previewWidth,
      previewHeight,
      showDetail,
      formatTime,
      ...modules,
    };
  },
};
</script>
<style lang="less" scoped>
.user {
  color: #4ca8ff;
  font-weight: 600;
}
.user:hover {
  cursor: pointer;
}
.alert-content {
  display: flex;
  justify-content: space-between;
}
.details-container {
  height: 100%;
  overflow-y: auto;
}
</style>
