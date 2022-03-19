import { h, ref } from 'vue';
import { NTag, NButton, NSpace, NTooltip, NGradientText } from 'naive-ui';

import ExpandedCard from '@/components/vmachineComponents/ExpandedCard';

import { deleteAjax } from '@/assets/CRUD/delete';
import { deleteVm } from '@/api/delete';
import { modifyDelayTime } from '@/api/put';
import { formatTime } from '@/assets/utils/dateFormatUtils';
import { get } from '@/assets/CRUD/read';
import vmachineTable from '@/views/vmachine/modules/vmachineTable.js';
import textDialog from '@/assets/utils/dialog';

const delayModalRef = ref();
const delay = ref({
  time: '',
  id: '',
});
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
    },
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
    render(row) {
      return h(
        NTooltip,
        {
          trigger: 'hover',
        },
        {
          trigger: () => {
            return h(
              NGradientText,
              {
                type: 'info',
                style: 'cursor:pointer',
                onClick: () => {
                  delay.value.time = new Date(row.end_time).getTime();
                  delay.value.id = row.id;
                  delayModalRef.value.show();
                },
              },
              row.end_time
            );
          },
          default: () => '延长期限',
        }
      );
    },
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
  },
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
        wrap: false,
      },
      [
        h(
          NButton,
          {
            size: 'small',
            type: 'error',
            disabled: !row.ip,
            onClick: () =>
              textDialog('warning', '警告', '你确定删除该虚拟机？', () => {
                deleteAjax.postDelete('/v1/vmachine', [row.id]);
              }),
          },
          '删除'
        ),
        h(
          NButton,
          {
            size: 'small',
            type: 'error',
            tertiary: true,
            onClick: () =>
              textDialog(
                'warning',
                '警告',
                '你确定要对此机器强制删除吗？(建议非特殊情况不要进行强制删除)',
                () => {
                  deleteVm(row.id);
                }
              ),
          },
          '强制删除'
        ),
      ]
    );
  },
};

const createColumns = () => {
  return [getColumnExpand(), ...ColumnDefault, ColumnState, ColumnOperate];
};
function submitDelay() {
  modifyDelayTime(delay.value.id, {
    end_time: formatTime(delay.value.time, 'yyyy-MM-dd hh:mm:ss'),
  }).then(() => {
    delay.value.id = '';
    delayModalRef.value.close();
    get.list('/v1/vmachine', vmachineTable.totalData, vmachineTable.loading);
  });
}

export { delay, delayModalRef, createColumns, submitDelay };
