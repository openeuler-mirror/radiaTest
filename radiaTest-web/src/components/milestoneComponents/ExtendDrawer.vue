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
      <n-tabs type="segment">
        <n-tab-pane name="image" tab="镜像信息">
          <div
            v-show="rowData.type !== 'update'"
            style="margin-top: 20px; margin-bottom: 20px"
          >
            <milestone-image-card :form="rowData" />
          </div>
          <div style="margin-top: 20px; margin-bottom: 20px">
            <milestone-repo-card :form="rowData" />
          </div>
        </n-tab-pane>
        <n-tab-pane name="issue" tab="Issues列表">
          <milestone-issues-card :milestone-id="rowData.id" />
        </n-tab-pane>
        <n-tab-pane name="task" tab="任务列表">
          <MilestoneTaskTable :milestoneId="rowData.id"/>
        </n-tab-pane>
      </n-tabs>
    </n-drawer-content>
  </n-drawer>
</template>

<script>
import { ref, defineComponent } from 'vue';

import MilestoneImageCard from './MilestoneImageCard.vue';
import MilestoneRepoCard from './MilestoneRepoCard.vue';
import MilestoneTaskTable from './MilestoneTaskTable.vue';
import MilestoneIssuesCard from './MilestoneIssuesCard.vue';
import { ArrowLeft32Filled as ArrowLeft } from '@vicons/fluent';

import milestoneTable from '@/views/versionManagement/milestone/modules/milestoneTable.js';

export default defineComponent({
  components: {
    MilestoneRepoCard,
    MilestoneImageCard,
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
