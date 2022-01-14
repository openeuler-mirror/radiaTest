<template>
  <div>
    <n-grid :cols="28" :x-gap="12" style="height: 100%">
      <n-gi :span="8">
        <case-timeline
          :records="records"
          :selectedRecord="selectedRecord"
          @handleline="handleline"
          @timeChange="timeChange"
          @checkdChange="checkdChange"
        />
      </n-gi>
      <n-gi :span="20">
        <div v-if="selectedRecord" class="logCard" style="overflow-y: scroll">
          <case-details
            :list="getAnalysisList(caseInfo, selectedRecord)"
            :logsData="logsData"
            :selectedStage="selectedStage"
            :selectedRecord="selectedRecord"
            @createIssue="newIssueRedirect(caseInfo.suite)"
            @updateEvent="emitUpdateEvent"
          />
        </div>
      </n-gi>
    </n-grid>
  </div>
</template>
<script>
import caseTimeline from '@/components/jobComponents/logsDrawerComponents/caseTimeline.vue';
import caseDetails from '@/components/jobComponents/logsDrawerComponents/caseDetails.vue';
import modules from './historicalExecModules';
import { inject, watch } from 'vue';
export default {
  props: ['case'],
  components: { caseDetails, caseTimeline },
  setup(props) {
    const caseInfo = inject('caseInfo');
    watch(caseInfo, (newVal) => {
      modules.getTimeline(newVal);
    });
    modules.getTimeline(props.case);
    return {
      caseInfo,
      ...modules
    };
  }
};
</script>
