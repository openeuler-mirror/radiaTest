import { h } from 'vue';
import { NButton, NIcon } from 'naive-ui';
import { Subtract20Filled } from '@vicons/fluent';

import { deleteDevice } from './deviceAjax';

const handleDeleteDisk = (id) => deleteDevice('/v1/vdisk', '磁盘', id);

const columns = [
  {
    key: 'used',
    title: '已用容量',
    className: 'cols',
  },
  {
    key: 'capacity',
    title: '磁盘容量',
    className: 'cols',
  },
  {
    key: 'bus',
    title: '磁盘总线',
    className: 'cols',
  },
  {
    key: 'cache',
    title: '缓存类型',
    className: 'cols',
  },
  {
    key: '',
    title: '操作',
    className: 'cols',
    render: (row) => {
      return h(
        NButton,
        {
          type: 'error',
          ghost: 'true',
          style: {
            width: '36px',
          },
          onClick: () => {
            handleDeleteDisk(row.id);
          },
        },
        h(NIcon, {}, h(Subtract20Filled, null))
      );
    },
  },
];

export default {
  columns,
  handleDeleteDisk,
};
