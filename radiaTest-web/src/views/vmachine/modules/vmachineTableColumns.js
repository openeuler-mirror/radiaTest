import { h } from 'vue';
import { NTag, NButton, NSpace } from 'naive-ui';

import ExpandedCard from '@/components/vmachineComponents/ExpandedCard';

import { deleteAjax } from '@/assets/CRUD/delete';

const getColumnExpand = () => {
  return {
    type: 'expand',
    renderExpand: (rowData) => {
      if (rowData.status === 'installing') {
        return h('div', null, '虚拟机正在安装');
      }
      return h(ExpandedCard, {
        data: rowData,
      });
    }
  };

};

const ColumnDefault = [
  {
    title: '虚拟机名称',
    key: 'name',
    className: 'cols vm-name',
  },
  {
    title: 'IP 地址',
    key: 'ip',
    className: 'cols ip',
  },
  {
    title: '架构',
    key: 'frame',
    className: 'cols frame',
  },
  {
    title: '宿主机 IP',
    key: 'host_ip',
    className: 'cols ip',
  },
  {
    title: '使用描述',
    key: 'description',
    className: 'cols description',
  },
  {
    title: '释放时间',
    key: 'end_time',
    className: 'cols end-time',
    sorter: true,
    sortOrder: false,
  },
];

const ColumnState = {
  title: '状态',
  key: 'status',
  className: 'cols state',
  render: (row) => {
    if (row.status === 'running') {
      return h(NTag, { type: 'error', round: true }, row.status);
    } else if (row.status === 'shut off') {
      return h(NTag, { color: 'grey', round: true }, row.status);
    }
    return h(NTag, { color: 'warning', round: true }, row.status);
  }
};

const ColumnOperate = {
  title: '操作',
  key: 'action',
  className: 'cols vmachine-operation',
  render: (row) => {
    return h(
      NSpace,
      {
        justify: 'center',
      },
      [
        h(
          NButton,
          {
            size: 'medium',
            type: 'error',
            text: true,
            disabled: !row.ip,
            onClick: () => deleteAjax.postDelete('/v1/vmachine', [row.id]),
          },
          '删除'
        ),
        h(
          NButton,
          {
            size: 'medium',
            type: 'info',
            text: true,
            disabled: true,
          },
          '延期'
        ),
      ]
    );
  },
};

const createColumns = () => {
  return [
    getColumnExpand(),
    ...ColumnDefault,
    ColumnState,
    ColumnOperate,
  ];
};

export {
  createColumns,
};

