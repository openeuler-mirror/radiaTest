<template>
  <n-card class="analyzedCard" hoverable>
    <div style="width: 100%; margin-bottom: 20px;">
      <n-space item-style="display: flex;" align="center" justify="start">
        <n-checkbox v-model:checked="failRecordsOnly">
          仅测试不通过
        </n-checkbox>
        <n-checkbox v-model:checked="sameMilestoneOnly">
          仅相同里程碑
        </n-checkbox>
      </n-space>
    </div>
    <n-date-picker
      v-model:value="recordsTimeRange"
      type="daterange"
      clearable
    />
    <timeline>
      <timeline-item
        v-for="(record, index) in records"
        :key="index"
        :type="createTimelineType(record.result)"
        :title="record.job"
        :left-width="300"
        :content="
          !record.fail_type && record.result === 'success'
            ? '测试通过'
            : record.fail_type
        "
        :tag="record.job_id === jobId ? '本次测试' : ''"
        :timestamp="record.create_time"
      >
        <n-radio
          :checked="selectedRecord === record"
          @change="
            (e) => {
              handleSelectRecord(record);
            }
          "
          :value="record"
          name="recordRadio"
        />
      </timeline-item>
    </timeline>
  </n-card>
</template>

<script>
import { defineComponent } from 'vue';

import Timeline from '@/components/timeline/timeline.vue';
import TimelineItem from '@/components/timeline/timelineItem.vue';

import logsDrawer from '@/views/job/modules/logsDrawer.js';

export default defineComponent({
  components: {
    Timeline,
    TimelineItem,
  },
  setup() {
    return {
      ...logsDrawer,
    };
  },
});
</script>

<style scoped>
.analyzedCard {
  height: 100%;
}
</style>
