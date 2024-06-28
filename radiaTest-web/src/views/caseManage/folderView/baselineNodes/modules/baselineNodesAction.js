import { ref } from 'vue';
import router from '@/router';
import { init } from 'echarts';
import { automationRatePie, contributionRatioPie } from '../../modules/echartsOptions';
import { getCaseNodeResource } from '@/api/get.js';

const suitesCount = ref(0);
const casesCount = ref(0);
const autoRatio = ref(0);
const typeDistribute = ref([]);

function echartConfig(chartId, options) {
  let chart;
  chart = init(document.querySelector(`#${chartId}`));
  chart?.clear();
  chart.setOption(options);
}

function initEcharts() {
  echartConfig('automationRate-pie', automationRatePie([{ label: '用例自动化率', value: autoRatio.value }], '用例自动化率'));
  echartConfig('distribution-pie', contributionRatioPie(typeDistribute.value, '用例分布'));
}

function initData() {
  const id = window.atob(router.currentRoute.value.params.taskId);
  getCaseNodeResource(id).then(res => {
    const { data } = res;
    suitesCount.value = data.suite_count;
    casesCount.value = data.case_count;
    autoRatio.value = parseInt(data.auto_ratio);
    typeDistribute.value = data.type_distribute;
    initEcharts();
  });
  initEcharts();
}

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
  initData,
  suitesCount,
  casesCount,
  autoRatio,
  typeDistribute,
  dispatchRefreshEvent,
};
