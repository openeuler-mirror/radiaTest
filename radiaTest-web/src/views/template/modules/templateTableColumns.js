import { h } from 'vue';
import { NButton, NSpace } from 'naive-ui';
import ExpandedCard from '@/components/templateComponents/ExpandedCard';

import { deleteAjax } from '@/assets/CRUD/delete';
import { handleExecClick } from './execTemplate';
import textDialog from '@/assets/utils/dialog';

const ColumnExpand = {
  type: 'expand',
  renderExpand: (rowData) =>
    h(ExpandedCard, {
      data: rowData.cases.map((item) => {
        return {
          name: item.name,
        };
      }),
    }),
};

const ColumnDefault = [
  {
    title: '模板名',
    key: 'name',
    className: 'cols',
  },
  {
    title: '关联里程碑',
    key: 'milestone',
    className: 'cols',
  },
  {
    title: '创建人',
    key: 'author',
    className: 'cols',
  },
  {
    title: '模板归属',
    key: 'owner',
    className: 'cols',
  },
  {
    title: '创建时间',
    key: 'create_time',
    className: 'cols',
  },
  {
    title: '更新时间',
    key: 'update_time',
    className: 'cols',
  },
  {
    title: '模板描述',
    key: 'description',
    className: 'cols',
  },
];

const getColumns = () => [
  ColumnExpand,
  ...ColumnDefault,
  {
    title: '操作',
    key: 'operation',
    fixed: 'right',
    className: 'cols',
    render: (row) => {
      return h(
        NSpace,
        {
          justify: 'center',
          align: 'center',
        },
        [
          h(
            NButton,
            {
              size: 'small',
              type: 'success',
              onClick: () => handleExecClick(row),
            },
            '执行'
          ),
          h(
            NButton,
            {
              text: true,
              color: 'rgba(242,93,93,1)',
              onClick: () => {
                textDialog('warning', '警告', '你确定要删除吗?', () =>
                  deleteAjax.postDelete(`/v1/template/${row.id}`)
                );
              },
            },
            '删除'
          ),
        ]
      );
    },
  },
];

export { getColumns };
