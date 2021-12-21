import { h } from 'vue';
import { NIcon, NButton } from 'naive-ui';
import { Construct } from '@vicons/ionicons5';
import { renderTooltip } from '@/assets/render/tooltip';

const createColumns = (handler) => {
  return [
    {
      title: '产品名',
      key: 'name',
      className: 'cols name',
    },
    {
      title: '版本名',
      key: 'version',
      className: 'cols version',
    },
    {
      title: '描述',
      key: 'description',
      className: 'cols description',
    },
    {
      title: '操作',
      key: 'action',
      className: 'cols operation',
      render: (row) => {
        return renderTooltip(
          h(
            NButton,
            {
              size: 'medium',
              type: 'warning',
              circle: true,
              onClick: () => handler(row),
            },
            h(NIcon, { size: '20' }, h(Construct))
          ),
          '修改'
        );
      },
    },
  ];
};

export default createColumns;

