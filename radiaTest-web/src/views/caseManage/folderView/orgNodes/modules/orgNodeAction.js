import { ref } from 'vue';
import { init } from 'echarts';
import { automationRatePie, contributionRatioPie, commitCountsBar, commitCountsLine } from './echartsOptions';
import { getOrgNode } from '@/api/get.js';
import router from '@/router';

const itemsCount = ref(0);
const commitMonthCount = ref(0);
const commitWeekCount = ref(0);

function echartConfig(chartId, options) {
  let chart;
  chart = init(document.querySelector(`#${chartId}`));
  chart?.clear();
  chart.setOption(options);
}

const autoRatio = ref(0);
const groupDistribute = ref([]);
const typeDistribute = ref([]);
const commitAttribute = ref([]);
const distribute = ref([]);

function initEcharts() {
  echartConfig('automationRate-pie', automationRatePie([{label:'用例自动化率', value: autoRatio.value}],'用例自动化率'));
  echartConfig('contributionRatio-pie', contributionRatioPie(groupDistribute.value,'用例贡献占比'));
  echartConfig('distribution-pie', contributionRatioPie(typeDistribute.value,'用例分布'));
  echartConfig('commitCounts-bar', commitCountsBar(commitAttribute.value,'用例commit合入'));
  echartConfig('commitCounts-line', commitCountsLine(distribute.value,'用例commit合入'));
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
  getOrgNode(router.currentRoute.value.query.id).then(res => {
    const { data } = res;
    itemsCount.value = data.all_count;
    commitMonthCount.value = data.month_count;
    commitWeekCount.value = data.week_count;
    autoRatio.value = parseInt(data.auto_ratio);
    commitAttribute.value = formatObject(data.commit_attribute);
    distribute.value = formatObject(data.distribute);
    groupDistribute.value = formatObject(data.group_distribute, 'name');
    typeDistribute.value = formatObject(data.type_distribute, 'name');
    initEcharts();
  });
}
export {
  itemsCount,
  commitMonthCount,
  commitWeekCount,
  initData
};
