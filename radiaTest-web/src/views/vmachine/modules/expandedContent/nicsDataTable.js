import { h } from 'vue';
import { NSpace, NButton } from 'naive-ui';

import { deleteDevice } from './deviceAjax';

const handleDeleteNic = (id) => deleteDevice('/v1/vnic', '网卡', id);

const columns = [
  {
    key: 'bus',
    title: '网卡总线',
    className: 'cols',
  },
  {
    key: 'mode',
    title: '网卡类型',
    className: 'cols',
  },
  {
    key: 'source',
    title: '网卡驱动',
    className: 'cols',
  },
  {
    key: 'ip',
    title: 'IP地址',
    className: 'cols',
  },
  {
    key: 'mac',
    title: 'MAC地址',
    className: 'cols',
  },
  {
    key: '',
    title: '操作',
    className: 'cols',
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
              type: 'error',
              ghost: true,
              onClick: () => {
                handleDeleteNic(row.id);
              },
            },
            '删除'
          ),
        ]
      );
    },
  },
];

export default {
  columns,
  handleDeleteNic,
};
