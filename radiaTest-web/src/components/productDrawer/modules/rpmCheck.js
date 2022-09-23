const resultDict = {
  prep_failed: '%prep失败',
  build_failed: '%build失败',
  check_failed: '%check失败',
  install_failed: '%install失败',
  success: '通过',
};

const columns = [
  {
    title: '软件包名',
    key: 'package',
  },
  {
    title: '架构',
    key: 'arch',
  },
  {
    title: 'build结果',
    key: 'result',
    render: (row) => {
      if (Object.keys(resultDict).includes(row.result)) {
        return resultDict[row.result];
      }
      return 'unknown';
    },
  },
  {
    title: '结果详情',
    key: 'detail',
  }
];

const data = ref([]);


export {
  columns,
  data,
};
