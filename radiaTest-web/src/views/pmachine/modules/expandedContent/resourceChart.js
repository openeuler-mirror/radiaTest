const staticLineChartOption = {
  grid: {
    left: '10%',
    right: '5%',
    bottom: '10%',
  },
  xAxis: {
    type: 'time',
    minInterval: 60 * 1000,
    splitLine: {
      show: false,
    },
  },
};

const initLineChart = (target, title, unit) => {
  target.setOption({
    title: {
      text: title,
      textStyle: {
        fontWeight: 'lighter',
        fontSize: 14,
        lineHeight: 36,
      },
    },
    ...staticLineChartOption,
    tooltip: {
      show: true,
      trigger: 'axis',
      formatter(params) {
        let str = `${params[0].data[0].toString()}<br />`;
        params.forEach((p) => {
          str += `${p.marker +
                    p.seriesName} : ${p.data[1].toString()}${unit}<br />`;
        });
        return str;
      },
      axisPointer: {
        animation: false,
      },
    },
    yAxis: {
      type: 'value',
      splitLine: {
        show: true,
      },
      axisLabel: {
        formatter: `{value}${unit}`,
      },
    },
  });
};

const staticPieChartOption = {
  tooltip: {
    trigger: 'item',
    formatter(params) {
      let str = `${params.seriesName}<br />${params.marker}${params.name} : ${params.data.value}%`;
      return str;
    },
  },
};

const initPieChart = (target, title, items, colorlist) => {
  target.setOption({
    title: {
      text: title,
      textStyle: {
        fontWeight: 'lighter',
        fontSize: 14,
        lineHeight: 36,
      },
    },
    ...staticPieChartOption,
    series: [
      {
        name: title,
        type: 'pie',
        itemStyle: {
          normal: {
            color(params) {
              let colorList = colorlist;
              return colorList[params.dataIndex];
            },
            label: {
              show: true,
              position: 'center',
              formatter: '{d}%',
              fontSize: 24,
              fontWeight: 'normal',
            },
          },
        },
        radius: ['50%', '70%'],
        avoidLabelOverlap: false,
        data: [
          { value: 0, name: items[0] },
          {
            value: 100,
            name: items[1],
            label: { show: false },
            labelLine: { show: false },
          },
        ],
      },
    ],
  });
};

const createEcharts = (charts) => {
  initLineChart(charts.performanceLine, '   服务器实时性能', '%');
  initPieChart(charts.cpuPie, 'CPU用量', ['已用', '空闲'], ['#2080f0', '#c4c4c4']);
  initPieChart(charts.memPie, '内存用量', ['已用', '空闲'], ['orange', '#c4c4c4']);
  initPieChart(
    charts.diskPie,
    '磁盘用量',
    ['已用', '空闲'],
    ['#920909', '#c4c4c4']
  );
  initLineChart(charts.networkLine, '   网络实时性能', 'KB/s');
  initPieChart(
    charts.swapPie,
    'swap用量',
    ['已用', '空闲'],
    ['orange', '#c4c4c4']
  );
};

const disposeEcharts = (charts) => {
  charts.performanceLine.dispose();
  charts.cpuPie.dispose();
  charts.memPie.dispose();
  charts.diskPie.dispose();
  charts.networkLine.dispose();
  charts.swapPie.dispose();
};

const setPerformanceLineOption = (charts, data) => {
  charts.performanceLine.setOption({
    xAxis: {
      min: data.performanceData.value[0][0],
    },
    yAxis: {
      min: 0,
      max: 100,
      splitNumber: 5,
    },
    series: [
      {
        type: 'line',
        showSymbol: false,
        itemStyle: {
          color: '#2080f0',
        },
        animation: false,
        name: 'CPU用量',
        data: data.performanceData.value.map((item) => [item[0], item[1]]),
      },
      {
        type: 'line',
        showSymbol: false,
        itemStyle: {
          color: 'orange',
        },
        name: 'Memory用量',
        animation: false,
        data: data.performanceData.value.map((item) => [item[0], item[2]]),
      },
      {
        type: 'line',
        showSymbol: false,
        itemStyle: {
          color: '#920909',
        },
        name: 'Disk用量',
        animation: false,
        data: data.performanceData.value.map((item) => [item[0], item[3]]),
      },
    ],
  });
};

const setCpuPieOption = (res, charts) => {
  charts.cpuPie.setOption({
    series: [
      {
        data: [
          { value: res.cpu_usage, name: '已用' },
          {
            value: 100 - res.cpu_usage,
            name: '空闲',
            label: { show: false },
            labelLine: { show: false },
          },
        ],
      },
    ],
  });
};

const setMemPieOption = (res, charts) => {
  charts.memPie.setOption({
    series: [
      {
        data: [
          { value: res.virtual_memory_usage, name: '已用' },
          {
            value: 100 - res.virtual_memory_usage,
            name: '空闲',
            label: { show: false },
            labelLine: { show: false },
          },
        ],
      },
    ],
  });
};

const setDiskPieOption = (res, charts) => {
  charts.diskPie.setOption({
    series: [
      {
        data: [
          { value: res.disk_usage, name: '已用' },
          {
            value: 100 - res.disk_usage,
            name: '空闲',
            label: { show: false },
            labelLine: { show: false },
          },
        ],
      },
    ],
  });
};

const setNetworkLineOption = (charts, data) => {
  charts.networkLine.setOption({
    xAxis: {
      min: data.networkData.value[0][0],
    },
    yAxis: {
      min: 0,
    },
    series: [
      {
        type: 'line',
        showSymbol: false,
        name: '下行速度',
        data: data.networkData.value.map((item) => [item[0], item[1]]),
        emphasis: {
          focus: 'series',
          blurScope: 'coordinateSystem',
        },
        areaStyle: {
          opacity: 0.2,
        },
        animation: false,
      },
      {
        type: 'line',
        showSymbol: false,
        name: '上行速度',
        data: data.networkData.value.map((item) => [item[0], item[2]]),
        areaStyle: {
          opacity: 0.2,
        },
        emphasis: {
          focus: 'series',
          blurScope: 'coordinateSystem',
        },
        animation: false,
      },
    ],
  });
};

const setSwapPieOptions = (res,charts) => {
  charts.swapPie.setOption({
    series: [
      {
        data: [
          { value: res.swap_memory_usage, name: '已用' },
          {
            value: 100 - res.swap_memory_usage,
            name: '空闲',
            label: { show: false },
            labelLine: { show: false },
          },
        ],
      },
    ],
  });
};

const listenResponse = (res, charts, data) => {
  data.performanceData.value.length > 600 ? data.performanceData.value.shift() : 0;
  data.networkData.value.length > 600 ? data.networkData.value.shift() : 0;
  data.performanceData.value.push([
    res.system_time,
    res.cpu_usage,
    res.virtual_memory_usage,
    res.disk_usage,
  ]);
  setPerformanceLineOption(charts, data);
  setCpuPieOption(res, charts);
  setMemPieOption(res, charts);
  setDiskPieOption(res, charts);
  data.networkData.value.push([
    res.system_time,
    res.net_input_speed / 1024,
    res.net_output_speed / 1024,
  ]);
  setNetworkLineOption(charts, data);
  setSwapPieOptions(res, charts);
  data.downloadSpeed.value = res.net_input_speed;
  data.uploadSpeed.value = res.net_output_speed;
  data.vmNum.value = res.running_vm_num;
  data.physicalCpuCores.value = res.cpu_physical_cores;
  data.logicalCpuCores.value = res.cpu_logical_cores;
  const byte2gib = 1024 ** -3;
  data.memoryTotal.value = (res.virtual_memory_total * byte2gib).toFixed(2);
  data.diskTotal.value = (res.disk_total * byte2gib).toFixed(2);
};

export default {
  createEcharts,
  disposeEcharts,
  listenResponse,
};
