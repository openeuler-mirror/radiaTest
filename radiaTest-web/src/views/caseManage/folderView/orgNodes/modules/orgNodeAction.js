import { ref } from 'vue';
import { init } from 'echarts';
import {
  automationRatePie,
  commitCountsLine
} from '../../modules/echartsOptions';
import { getOrgNode } from '@/api/get.js';
import router from '@/router';

const currentId = ref();
const suitesCount = ref(0);
const casesCount = ref(0);
const commitsCount = ref(0);

const commitSelectedTime = ref('week');
const timeOptions = ref([
  { label: '近一周', value: 'week' },
  { label: '近半月', value: 'halfMonth' },
  { label: '近一月', value: 'month' },
]);

function echartConfig(chartId, options) {
  let chart;
  chart = init(document.querySelector(`#${chartId}`));
  chart?.clear();
  chart.setOption(options);
}

const autoRatio = ref(0);
const distribute = ref([]);

function initEcharts() {
  echartConfig('orgAutomationRate-pie', automationRatePie([{ label: '用例自动化率', value: autoRatio.value }], '用例自动化率'));
  echartConfig('orgCommitCounts-line', commitCountsLine(distribute.value, '用例commit合入'));
}

function formatObject(data, prop) {
  let res = [];
  const p = prop || 'label';
  const keys = Object.keys(data);
  keys.forEach(key => {
    let item = {};
    item[p] = key;
    item.value = data[key];
    res.push(item);
  });
  return res;
}

function initData() {
  currentId.value = window.atob(router.currentRoute.value.params.taskId);
  getOrgNode(
    currentId.value,
    { commit_type: commitSelectedTime.value }
  )
    .then(res => {
      const { data } = res;
      suitesCount.value = data.suite_count;
      casesCount.value = data.case_count;
      // commitsCount.value = data.commmit_count;
      autoRatio.value = parseInt(data.auto_ratio);
      distribute.value = formatObject(data.distribute);
      initEcharts();
    });
}

watch(commitSelectedTime, () => { initData(); });

function dispatchRefreshEvent() {
  window.dispatchEvent(
    new CustomEvent('rootRefreshEvent', {
      detail: {
        type: 'org',
        id: window.atob(router.currentRoute.value.params.taskId)
      },
    })
  );
}

export {
  suitesCount,
  casesCount,
  commitsCount,
  initData,
  dispatchRefreshEvent,
  currentId,
  commitSelectedTime,
  timeOptions,
};
