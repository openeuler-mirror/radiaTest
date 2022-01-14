<template>
  <n-drawer v-model:show="active" :width="1800" :placement="right">
    <n-drawer-content
      header-style="justify-content: center;"
      body-style="background-color: rgba(240,241,244,1)"
    >
      <template #header>
        <p style="width: 1700px; text-align: center; margin: 0">
          <n-button
            @click="
              () => {
                active = false;
              }
            "
            size="medium"
            style="float: left"
            quaternary
            circle
          >
            <n-icon :size="26">
              <arrow-left />
            </n-icon>
          </n-button>
          <span style="line-height: 34px; font-size: 28px">
            {{ title }}
          </span>
        </p>
      </template>
      <n-grid :cols="36" :x-gap="12" style="height: 100%">
        <n-gi :span="8">
          <cases-selector />
        </n-gi>
        <n-gi :span="8">
          <analysis-timeline />
        </n-gi>
        <n-gi :span="20">
          <div v-if="selectedRecord" class="logCard" style="overflow-y: scroll">
            <case-details
              :list="getAnalysisList(caseDetail, selectedRecord)"
              :logsData="logsData"
              :selectedStage="selectedStage"
              :selectedRecord="selectedRecord"
              @createIssue="handleNewIssueRedirect(caseDetail.suite)"
              @updateEvent="emitUpdateEvent"
            />
          </div>
        </n-gi>
      </n-grid>
    </n-drawer-content>
  </n-drawer>
</template>

<script>
import { defineComponent } from 'vue';

import { ArrowLeft32Filled as ArrowLeft } from '@vicons/fluent';
import CasesSelector from './logsDrawerComponents/CasesSelector.vue';
import AnalysisTimeline from './logsDrawerComponents/AnalysisTimeline.vue';

import logsDrawer from '@/views/job/modules/logsDrawer.js';
import caseDetails from './logsDrawerComponents/caseDetails.vue';

export default defineComponent({
  components: {
    caseDetails,
    ArrowLeft,
    CasesSelector,
    AnalysisTimeline,
  },
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
.analyzedCard {
  height: 100%;
}
.logCard {
  height: 100%;
}
.logArea {
  height: 80%;
  border-style: none;
  box-shadow: 0 0 10px #f5f6f8;
  background-color: white;
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
