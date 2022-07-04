import { ref } from 'vue';
import { init } from 'echarts';
import { automationRatePie, commitCountsLine } from '../../orgNodes/modules/echartsOptions';
import { getTermNode } from '@/api/get.js';
import router from '@/router';
const itemsCount = ref(0);
const commitMonthCount = ref(0);
const commitWeekCount = ref(0);
const autoRatio = ref(0);

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
  getTermNode(router.currentRoute.value.query.id).then(res => {
    const { data } = res;
    itemsCount.value = data.all_count;
    commitMonthCount.value = data.month_count;
    commitWeekCount.value = data.week_count;
    autoRatio.value = parseInt(data.auto_ratio);
    distribute.value = formatObject(data.distribute);
    initEcharts();
  });
}
export {
  itemsCount,
  commitMonthCount,
  commitWeekCount,
  initData
};
