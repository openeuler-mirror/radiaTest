import { h } from 'vue';
import { NIcon, NButton, NSpace } from 'naive-ui';
import { Construct } from '@vicons/ionicons5';
import { renderTooltip } from '@/assets/render/tooltip';

const defaultColumns = [
  {
    title: '测试套',
    key: 'suite',
    className: 'cols suite',
  },
  {
    title: '用例名',
    key: 'name',
    className: 'cols case-name',
  },
  {
    title: '测试级别',
    key: 'test_level',
    className: 'cols test-level',
  },
  {
    title: '测试类型',
    key: 'test_type',
    className: 'cols test-type',
  },
  {
    title: '节点数',
    key: 'machine_num',
    className: 'cols machine-num',
  },
  {
    title: '节点类型',
    key: 'machine_type',
    className: 'cols machine-type',
  },
  {
    title: '自动化',
    key: 'automatic',
    className: 'cols auto',
    render(row) {
      if (row.automatic) {
        return h('p', null, '是');
      }
      return h('p', null, '否');
    },
  },
  {
    title: '备注',
    key: 'remark',
    className: 'cols remark',
  },
  {
    title: '责任人',
    key: 'owner',
    className: 'cols owner',
  },
];

const createColumns = (handler) => {
  return [
    ...defaultColumns,
    {
      title: '操作',
      key: 'action',
      className: 'cols operation',
      render: (row) => {
        return h(
          NSpace,
          {
            justify: 'center',
            align: 'cemter',
          },
          [
            renderTooltip(
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
            ),

          ]
        );
      },
    },
  ];
};

export default createColumns;
