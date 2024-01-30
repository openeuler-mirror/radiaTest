import { ref } from 'vue';
import { init } from 'echarts';
import {
  automationRatePie,
  contributionRatioPie,
  // commitCountsBar,
  // commitCountsLine,
} from '../../modules/echartsOptions';
import { getCaseNodeResource } from '@/api/get.js';
import router from '@/router';

const suitesCount = ref(0);
const casesCount = ref(0);
const commitsCount = ref(0);

function echartConfig(chartId, options) {
  let chart;
  chart = init(document.querySelector(`#${chartId}`));
  chart?.clear();
  chart.setOption(options);
}

const autoRatio = ref(0);
const typeDistribute = ref([]);
const commitAttribute = ref([]);
const distribute = ref([]);

const commitSelectedTime = ref('week');
const timeOptions = ref([
  { label: '近一周', value: 'week' },
  { label: '近半月', value: 'halfMonth' },
  { label: '近一月', value: 'month' },
]);

function initEcharts() {
  echartConfig('automationRate-pie', automationRatePie([{ label: '用例自动化率', value: autoRatio.value }], '用例自动化率'));
  echartConfig('distribution-pie', contributionRatioPie(typeDistribute.value, '用例分布'));
  // echartConfig('commitCounts-bar', commitCountsBar(commitAttribute.value, '用例commit合入'));
  // echartConfig('commitCounts-line', commitCountsLine(distribute.value, '用例commit合入'));
}

function formatObject(data, prop) {
  let res = [];
  const p = prop || 'label';
  const keys = data ? Object.keys(data) : null;
  keys?.forEach(key => {
    let item = {};
    item[p] = key;
    item.value = data[key];
    res.push(item);
  });
  return res;
}

function initData() {
  const id = window.atob(router.currentRoute.value.params.taskId);
  getCaseNodeResource(id, {
    commit_type: commitSelectedTime.value,
  })
    .then(res => {
      const { data } = res;
      suitesCount.value = data.suite_count;
      casesCount.value = data.case_count;
      commitsCount.value = data.commit_count;
      autoRatio.value = parseInt(data.auto_ratio);
      commitAttribute.value = formatObject(data.commit_attribute);
      distribute.value = formatObject(data.distribute);
      typeDistribute.value = data.type_distribute;
      initEcharts();
    });
  initEcharts();
}

watch(commitSelectedTime, () => { initData(); });

function dispatchRefreshEvent() {
  window.dispatchEvent(
    new CustomEvent('refreshEvent', {
      detail: {
        caseNodeId: window.atob(router.currentRoute.value.params.taskId)
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
