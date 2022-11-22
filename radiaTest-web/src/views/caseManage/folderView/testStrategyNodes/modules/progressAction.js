import { ref } from 'vue';
import { init } from 'echarts';
import { automationRatePie } from './echartsOptions';

const softwareCount = ref(5);
const testCount = ref(5);
const exampleCount = ref(34);
const autoExampleCount = ref(17);
const finishTime = ref('2022/09/30');

function echartConfig(chartId, options) {
  let chart;
  chart = init(document.querySelector(`#${chartId}`));
  chart?.clear();
  chart.setOption(options);
}

const autoExamplesList = [
  {
    label: 'oe_testcase_jq_004',
    responsible: 'DisNight',
    helper: 'Ethan-zhang',
    startTime: '2022/06/28',
    endTime: '2022/08/30',
    percentage: 0
  },
  {
    label: 'oe_testcase_jq_001',
    responsible: 'DisNight',
    helper: 'Ethan-zhang',
    startTime: '2022/06/28',
    endTime: '2022/08/30',
    percentage: 80
  },
  {
    label: 'oe_testcase_jq_002',
    responsible: 'DisNight',
    helper: 'Ethan-zhang',
    startTime: '2022/06/28',
    endTime: '2022/08/30',
    percentage: 10
  },
  {
    label: 'oe_testcase_jq_003',
    responsible: 'DisNight',
    helper: 'Ethan-zhang',
    startTime: '2022/06/28',
    endTime: '2022/08/30',
    percentage: 50
  }
];

function createTask() {
  console.log('val11111111111');
}

function initEcharts() {
  echartConfig('testPie', automationRatePie([{label:'用例自动化率', value: 60}],''));
  echartConfig('examplePie', automationRatePie([{label:'用例自动化率', value: 40}],''));
}

function progressInit() {
  initEcharts();
}

export {
  softwareCount,
  testCount,
  exampleCount,
  autoExampleCount,
  finishTime,
  autoExamplesList,
  createTask,
  progressInit
};
