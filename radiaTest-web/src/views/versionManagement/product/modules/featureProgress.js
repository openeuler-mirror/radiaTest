const featureOption = {
  tooltip: {
    trigger: 'item'
  },
  title: {
    textStyle: {
      fontSize: '14',
    },
  },
  color: ['#18a058', '#2080f0', '#d1d1d1'],
  series: [
    {
      type: 'pie',
      left: 30,
      radius: ['50%', '70%'],
      avoidLabelOverlap: false,
      data: [
        { name: 'Accepted', value: 0 },
        { name: 'Testing', value: 0 },
        { name: 'Developing', value: 0 },
      ]
    }
  ]
};

function setFeatureOption(option, title, data) {
  option.title.text = title;
  option.title.subtext = `完成度${data.accepted_rate}%`;
  option.series[0].data = [
    { name: 'Accepted', value: data.accepted_count },
    { name: 'Testing', value: data.testing_count },
    { name: 'Developing', value: data.developing_count },
  ];
}

export {
  featureOption,
  setFeatureOption,
};
