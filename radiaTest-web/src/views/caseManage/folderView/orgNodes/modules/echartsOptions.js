function commonConfig(title, bottom) {
  return {
    title: {
      text: title,
      left: 'center',
      bottom: bottom || '5%',
      textStyle: {
        color: '#000000',
        fontSize: 14,
        align: 'center'
      }
    }
  };
}
function automationRatePie(data,title)  {
  const options = {
    ...commonConfig(title),
    series: [{
      type: 'pie',
      clockWise: false,
      radius: ['60%', '70%'],
      itemStyle:  {
        normal: {
          color: '#389af4',
          shadowColor: '#389af4',
          shadowBlur: 0,
          label: { show: false },
          labelLine: { show: false },
        }
      },
      hoverAnimation: false,
      center: ['50%', '45%'],
      data: [{
        value: data[0].value,
        label: {
          normal: {
            formatter(params){
              return `${params.value}%`;
            },
            position: 'center',
            show: true,
            textStyle: {
              fontSize: '20',
              fontWeight: 'bold',
              color: '#389af4'
            }
          }
        },
      }, {
        value: 100-(data[0].value),
        name: '',
        itemStyle: {
          normal: {
            color: '#dfeaff'
          },
          emphasis: {
            color: '#dfeaff'
          }
        }
      }]
    }]
  };
  return options;
}

function contributionRatioPie(data,title) {
  const options = {
    ...commonConfig(title),
    tooltip: {
      trigger: 'item'
    },
    legend: {
      orient: 'vertical',
      left: 'right',
      icon: 'circle',
      align:'left',
    },
    series: [
      {
        name: '',
        type: 'pie',
        radius: '50%',
        data,
        label: {
          normal: {
            position: 'inner',
            fontSize: 12,
            formatter(params) {
              return `${params.percent}%`;
            }
          }
        },
        itemStyle:  {
          normal: {
            label: { 
              color:'#ffffff',
              show: true
            },
            labelLine: { show: false },
          }
        },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowOffsetX: 0,
            shadowColor: 'rgba(0, 0, 0, 0.5)'
          }
        }
      }
    ]
  };
  return options;
}

function commitCountsBar(data, title) {
  let yAxis = [];
  let list = [];
  data.map(item => {
    yAxis.push(item.label);
    list.push(item.value);
  });
  const options = {
    ...commonConfig(title, '0%'),
    grid: {
      left: '3%',
      right: '4%',
      bottom: '10%',
      containLabel: true
    },
    xAxis: {
      type: 'value',
      axisLine: {
        show: true
      }
    },
    yAxis: {
      type: 'category',
      data: yAxis
    },
    series: [
      {
        name: '用例commit合入',
        type: 'bar',
        data: list,
        barWidth: 20,
        label: {
          show: true,
        }
      },
    ]
  };
  return options;
}

function commitCountsLine(data, title) {
  let xAxis = [];
  let list = [];
  data.map(item => {
    xAxis.push(item.label);
    list.push(item.value);
  });
  const options = {
    ...commonConfig(title, '0%'),
    grid: {
      left: '3%',
      right: 20,
      bottom: '10%',
      top:40,
      containLabel: true
    },
    xAxis: {
      type: 'category',
      data: xAxis
    },
    yAxis: {
      type: 'value'
    },
    series: [
      {
        data: list,
        type: 'line',
        symbol: 'triangle',
        symbolSize: 10,
        label: {
          show: true,
        }
      }
    ]
  };
  return options;
}

function testItemBaselineTree(data) {
  const options = {
    tooltip: {
      trigger: 'item',
      triggerOn: 'mousemove'
    },
    series: [
      {
        type: 'tree',
        id: 0,
        name: 'tree1',
        data,
        top: '10%',
        left: '8%',
        bottom: '10%',
        right: '10%',
        width:'100%',
        symbolSize: 7,
        edgeShape: 'polyline',
        edgeForkPosition: '63%',
        initialTreeDepth: 3,
        orient: 'vertical',
        lineStyle: {
          width: 2
        },
        label: {
          backgroundColor: '#fff',
          position: 'left',
          verticalAlign: 'middle',
          align: 'right'
        },
        leaves: {
          label: {
            position: 'right',
            verticalAlign: 'middle',
            align: 'left'
          }
        },
        emphasis: {
          focus: 'descendant'
        },
        expandAndCollapse: true,
        animationDuration: 550,
        animationDurationUpdate: 750
      }
    ]
  };
  return options;
}

export {
  automationRatePie,
  contributionRatioPie,
  commitCountsBar,
  commitCountsLine,
  testItemBaselineTree
};
