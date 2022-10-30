function createDefaultColumns(renderIcon) {
  return [
    {
      key: 'name',
      title: '软件包',
    },
    {
      key: 'design',
      title: '测试设计',
      render: (row) => renderIcon(row, '测试设计'),
    },
    {
      key: 'develop',
      title: '用例开发',
      render: (row) => renderIcon(row, '用例开发'),
    },
    {
      key: 'execute',
      title: '测试执行',
      render: (row) => renderIcon(row, '已执行'),
    },
    {
      key: 'analyze',
      title: '问题分析',
      render: (row) => renderIcon(row, '问题分析'),
    },
  ];
}

export {
  createDefaultColumns
};
