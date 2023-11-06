<template>
  <n-card class="analyzedCard" hoverable>
    <div style="width: 100%; margin-bottom: 20px; display: flex">
      <n-space item-style="display: flex;" align="center" justify="start">
        <n-checkbox v-model:checked="failRecordsOnly" @update:checked="handleCheck">
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
        :content="resultContent(record.result, record.fail_type)"
        :tag="record.job_id === jobId ? '本次测试' : ''"
        :timestamp="record.create_time"
      >
        <div style="width: 90px; display: flex; justify-content: space-between; margin-left: -46px">
          <n-tag type="info">{{ record.manual ? '手工' : '自动化' }} </n-tag>
          <n-radio-button
            :checked="selectedRecord === record"
            @change="handleSelectRecord(record)"
            :value="record"
            label=""
            name="recordRadio"
          />
        </div>
      </timeline-item>
    </timeline>
  </n-card>
</template>

<script>
import { defineComponent, ref } from 'vue';
import Timeline from '@/components/timeline/timeline.vue';
import TimelineItem from '@/components/timeline/timelineItem.vue';
import axios from '@/axios';
import { workspace } from '@/assets/config/menu.js';

function resultType(result) {
  if (result === 'success') {
    return 'success';
  } else if (result === 'fail') {
    return 'error';
  } else if (result === 'block') {
    return 'warning';
  }
  return 'default';
}
function resultContent(result, type) {
  if (!type && result === 'success') {
    return '测试通过';
  } else if (result === 'fail') {
    return '测试失败';
  } else if (result === 'block') {
    return '测试阻塞';
  }
  return '正在执行';
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
    },
  },
  setup() {
    const recordsTimeRange = ref([0, Date.now()]);
    const failRecordsOnly = ref(false);
    const milestone = ref();
    const milestoneList = ref([]);
    axios
      .get(`/v2/ws/${workspace.value}/milestone`)
      .then((res) => {
        milestoneList.value = res.data?.items.map((item) => ({ label: item.name, value: item.id }));
      })
      .catch((err) => window.$message?.error(err.data.error_msg || '未知错误'));
    return {
      recordsTimeRange,
      milestone,
      milestoneList,
      failRecordsOnly,
      resultType,
      resultContent,
    };
  },
});
</script>

<style scoped>
.analyzedCard {
  height: 100%;
}
</style>
