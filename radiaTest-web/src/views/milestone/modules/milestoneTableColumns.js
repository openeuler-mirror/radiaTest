import { h } from 'vue';
import { NIcon, NButton, NTag, NSpace } from 'naive-ui';
import { Construct } from '@vicons/ionicons5';
import { renderTooltip } from '@/assets/render/tooltip';

const constColumns = [
  {
    title: '产品名',
    key: 'product_name',
    className: 'cols product-name',
  },
  {
    title: '版本名',
    key: 'product_version',
    className: 'cols product-version',
  },
  {
    title: '里程碑名',
    key: 'name',
    className: 'cols milestone-name',
  },
  {
    title: '里程碑类型',
    key: 'type',
    className: 'cols milestone-type',
  },
  {
    title: '开始时间',
    key: 'start_time',
    className: 'cols start-time',
  },
  {
    title: '结束时间',
    key: 'end_time',
    className: 'cols end-time',
  },
  {
    title: '任务数',
    key: 'task_num',
    className: 'cols task',
  },
];

const createColumns = (handler) => {
  return [
    ...constColumns,
    {
      title: '镜像标签',
      key: 'tags',
      className: 'cols tags',
      render: (row) => {
        if (row.tags) {
          const hTags = row.tags.map((item) => {
            return h(
              NTag,
              {
                type: 'success',
              },
              item
            );
          });
          return h(NSpace, { justify: 'center' }, hTags);
        }
        return h();
      },
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
