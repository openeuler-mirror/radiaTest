<template>
  <n-card class="analyzedCard" hoverable>
    <div style="width: 100%; margin-bottom: 20px; display: flex">
      <n-space item-style="display: flex;" align="center" justify="start">
        <n-checkbox
          v-model:checked="failRecordsOnly"
          @update:checked="handleCheck"
        >
          仅测试不通过
        </n-checkbox>
      </n-space>
      <n-select
        v-model:value="milestone"
        :options="milestoneList"
        @update:value="handleCheck"
        clearable
        placeholder="选择里程碑"
      ></n-select>
    </div>
    <n-date-picker
      v-model:value="recordsTimeRange"
      @update:value="timeRangeChange"
      type="daterange"
      clearable
    />
    <timeline>
      <timeline-item
        v-for="(record, index) in records"
        :key="index"
        :type="resultType(record.result)"
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
          @change="handleSelectRecord(record)"
          :value="record"
          name="recordRadio"
        />
      </timeline-item>
    </timeline>
  </n-card>
</template>

<script>
import { defineComponent, ref } from 'vue';

import Timeline from '@/components/timeline/timeline.vue';
import TimelineItem from '@/components/timeline/timelineItem.vue';
import axios from '@/axios';
function resultType(result) {
  if (result === 'success') {
    return 'success';
  } else if (result === 'fail') {
    return 'error';
  }
  return 'default';
}


export default defineComponent({
  props: ['records', 'selectedRecord'],
  components: {
    Timeline,
    TimelineItem,
  },
  methods: {
    handleSelectRecord(record) {
      this.$emit('handleline', record);
    },
    timeRangeChange() {
      this.$emit('timeChange', this.recordsTimeRange);
    },
    handleCheck() {
      this.$emit('checkdChange', { records: this.failRecordsOnly, milestone: this.milestone });
    }
  },
  setup() {
    const recordsTimeRange = ref([0, Date.now()]);
    const failRecordsOnly = ref(false);
    const milestone = ref();
    const milestoneList = ref([]);
    axios.get('/v2/milestone').then(res => {
      milestoneList.value = res.data?.items.map(item => ({ label: item.name, value: item.id }));
    }).catch(err => window.$message?.error(err.data.error_msg || '未知错误'));
    return {
      recordsTimeRange,
      milestone,
      milestoneList,
      failRecordsOnly,
      resultType
    };
  },
});
</script>

<style scoped>
.analyzedCard {
  height: 100%;
}
</style>
