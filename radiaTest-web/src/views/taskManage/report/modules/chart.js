import { reactive } from 'vue';

import axios from '@/axios';
import { timeRange, type, milestone, owner, ownerOptions } from './screen';
import { formatTime } from '@/assets/utils/dateFormatUtils.js';
import { setTableDate } from './issueTable';

const count = reactive({
  incomplete: 0,
  completed: 0,
  total: 0,
  dueToday: 0,
  overdue: 0,
});

const lineOptions = reactive({
  title: {
    text: '任务燃尽图'
  },
  tooltip: {
    trigger: 'axis'
  },
  legend: {
    data: ['计划', '实际']
  },
  grid: {
    left: '3%',
    right: '4%',
    bottom: '3%',
    containLabel: true
  },
  xAxis: {
    type: 'category',
    boundaryGap: false,
    data: []
  },
  yAxis: {
    type: 'value'
  },
  series: [
    {
      name: '计划',
      type: 'line',
      data: []
    },
    {
      name: '实际',
      type: 'line',
      data: [],
    },
  ]
});

const pieOption = reactive({
  title: {
    text: '任务分布图',
  },
  tooltip: {
    trigger: 'item'
  },
  legend: {
    orient: 'vertical',
    left: 'right'
  },
  series: [
    {
      name: '任务分布图',
      type: 'pie',
      radius: '50%',
      data: [],
      emphasis: {
        itemStyle: {
          shadowBlur: 10,
          shadowOffsetX: 0,
          shadowColor: 'rgba(0, 0, 0, 0.5)'
        }
      }
    }
  ]
});
const barOptions = reactive({
  title: {
    text: '期间逾期的任务',
  },
  xAxis: {
    type: 'category',
    name: '人员',
    data: [],
    axisLabel: {
      rotate: 10
    }
  },
  yAxis: {
    type: 'value',
    name: '任务数'
  },
  series: [
    {
      data: [],
      type: 'bar',
      barMaxWidth: 40,
    }
  ]
});
function setDataZoom (option, maxCount, dataLength) {
  option.dataZoom = [
    {
      type: 'slider',
      show: true,
      xAxisIndex: [0],
      start: 1,
      height: '5%',
      bottom: '2%',
      end: maxCount * 100 / dataLength
    },
  ];
}
function getData () {
  const [executors, groups] = [[], []];
  owner.value.forEach(item => {
    const element = ownerOptions.value.find(i => {
      return item === i.value;
    });
    element.type === 'GROUP' ? groups.push(item) : executors.push(item);
  });
  const option = {
    start_time: formatTime(timeRange.value ? timeRange.value[0] : null, 'yyyy-MM-dd'),
    end_time: formatTime(timeRange.value ? timeRange.value[1] : null, 'yyyy-MM-dd'),
    type: type.value,
    executors: executors.join(','),
    milestone_id: milestone.value,
    groups: groups.join(','),
  };
  axios.get('/v1/task/count/total', option).then(res => {
    count.dueToday = res.data.count_today;
    count.overdue = res.data.overtime_count;
    count.completed = res.data.accomplish;
    count.incomplete = res.data.not_accomplish;
    count.total = res.data.total;
    const pieKeys = Object.keys(res.data.task_distribute);
    pieOption.series[0].data = [];
    for (const item of pieKeys) {
      pieOption.series[0].data.push({ value: res.data.task_distribute[item], name: item });
    }
    const barKeys = Object.keys(res.data.task_overtime);
    const barValues = Object.values(res.data.task_overtime);
    barOptions.series[0].data = barValues;
    barOptions.xAxis.data = barKeys;
    if (barKeys.length > 7) {
      setDataZoom(barOptions, 7, barKeys.length);
    }
    lineOptions.xAxis.data = res.data.burn_down_time;
    lineOptions.series[1].data = res.data.burn_down_count;
    const arr = [];
    const step = res.data.total / (res.data.total_day - 1);
    for (let i = 0; i < res.data.total_day; i++) {
      arr.push(res.data.total - (step * i));
    }
    lineOptions.series[0].data = arr;
    setTableDate(res.data.issues);
  }).catch(err => {
    window.$message.error(err.data.error_msg||'未知错误');
  });
}


export {
  lineOptions,
  barOptions,
  pieOption,
  count,
  getData,
};
