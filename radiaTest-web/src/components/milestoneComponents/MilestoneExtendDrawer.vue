<template>
  <n-drawer v-model:show="active" :width="1600" placement="right">
    <n-drawer-content>
      <template #header>
        <p style="width: 1500px; text-align: center; margin: 0">
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
            {{ rowData.name }}
          </span>
        </p>
      </template>
      <n-tabs animated type="segment">
        <n-tab-pane name="issue" tab="Issues列表">
          <milestone-issues-card :milestone-id="rowData.id" />
        </n-tab-pane>
        <n-tab-pane name="task" tab="任务列表">
          <MilestoneTaskTable :milestoneId="rowData.id" />
        </n-tab-pane>
      </n-tabs>
    </n-drawer-content>
  </n-drawer>
</template>

<script>
import { ref, defineComponent } from 'vue';

import MilestoneTaskTable from './MilestoneTaskTable.vue';
import MilestoneIssuesCard from './MilestoneIssuesCard.vue';
import { ArrowLeft32Filled as ArrowLeft } from '@vicons/fluent';

import milestoneTable from '@/views/versionManagement/milestone/modules/milestoneTable.js';

export default defineComponent({
  components: {
    MilestoneIssuesCard,
    MilestoneTaskTable,
    ArrowLeft,
  },
  setup() {
    return {
      active: milestoneTable.active,
      rowData: milestoneTable.rowData,
      showIssuesDrawer: ref(false),
      issueDrawerRef: ref(null),
    };
  },
});
</script>
