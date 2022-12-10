import { ref } from 'vue';
import { init } from 'echarts';
import { automationRatePie, commitCountsLine } from '../../modules/echartsOptions';
import { getTermNode } from '@/api/get.js';
import router from '@/router';

const suitesCount = ref(0);
const casesCount = ref(0);
const commitsCount = ref(0);
const autoRatio = ref(0);

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

const distribute =ref([]);
function initEcharts() {
  echartConfig('termAutomationRate-pie', automationRatePie([{label:'用例自动化率', value: autoRatio.value}],'用例自动化率'));
  echartConfig('termCommitCounts-line', commitCountsLine(distribute.value,'用例commit合入'));
}

function formatObject(data) {
  let res = [];
  const keys = Object.keys(data);
  keys.forEach(key => {
    res.push({
      label: key,
      value: data[key]
    });
  });
  return res;
}

function initData() {
  getTermNode(
    window.atob(router.currentRoute.value.params.taskId),
    { commit_type: commitSelectedTime.value }  
  )
    .then(res => {
      const { data } = res;
      suitesCount.value = data.suite_count;
      casesCount.value = data.case_count;
      commitsCount.value = data.commit_count;
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
        type: 'group',
        id: window.atob(router.currentRoute.value.params.taskId)
      },
    })
  );
}

export {
  suitesCount,
  casesCount,
  commitsCount,
  commitSelectedTime,
  timeOptions,
  initData,
  dispatchRefreshEvent,
};
