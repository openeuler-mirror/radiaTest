import { h, ref } from 'vue';
import { NTag, NIcon, NButton, NSpace, NTooltip, NGradientText } from 'naive-ui';

import ExpandedCardVmachine from '@/components/vmachineComponents/ExpandedCardVmachine';

import { deleteAjax } from '@/assets/CRUD/delete';
import { deleteVm } from '@/api/delete';
import { modifyDelayTime, modifyVmachineIp } from '@/api/put';
import { formatTime } from '@/assets/utils/dateFormatUtils';
import textDialog from '@/assets/utils/dialog';
import { WarningRound } from '@vicons/material';
import { validateIpaddress } from '@/assets/utils/formUtils';

const ipaddrModalRef = ref();
const ipaddr = ref({
  ip: '',
  id: '',
});

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
      } else if (!rowData.ip && (!rowData.vnc_token || rowData.vnc_port === null)) {
        return h('div', null, '缺乏IP以及VNC相关参数，该虚拟机暂不可用');
      }
      return h(ExpandedCardVmachine, {
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
    title: '版本',
    key: 'product',
  },
  {
    title: 'IP 地址',
    key: 'ip',
    align: 'center',
    className: 'cols ip',
    render(row) {
      return h(
        NTooltip,
        {
          trigger: 'hover',
        },
        {
          trigger: () => {
            return h(
              'p',
              {
                style: {
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: 'pointer'
                },
                onClick: () => {
                  ipaddr.value.ip = row.ip;
                  ipaddr.value.id = row.id;
                  ipaddrModalRef.value.show();
                },
              },
              row.ip
                ? h(NGradientText, { type: 'info' }, row.ip)
                : [
                  h(
                    NIcon,
                    {
                      color: 'grey',
                      size: 18,
                    },
                    {
                      default: () => h(WarningRound)
                    }
                  ),
                  h('span', { style: { color: 'grey' } }, 'Unknown')
                ]
            );
          },
          default: () => row.ip ? '若IP发生变动，此处需要手动变更' : 'IP未分配，若已有IP需要手动录入',
        }
      );
    }
  },
  {
    title: '架构',
    align: 'center',
    key: 'frame',
    className: 'cols frame',
  },
  {
    title: '宿主机 IP',
    align: 'center',
    key: 'host_ip',
    className: 'cols ip',
  },
  {
    title: '使用描述',
    align: 'center',
    key: 'description',
    className: 'cols description',
  },
  {
    title: '释放时间',
    align: 'center',
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
  align: 'center',
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
  align: 'center',
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
                deleteAjax.singleDelete(`/v1/vmachine/${row.id}`, row.id);
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
  });
}

function submitIpaddr() {
  modifyVmachineIp(ipaddr.value.id, {
    ip: ipaddr.value.ip,
  }).then(() => {
    ipaddr.value.id = '';
    ipaddrModalRef.value.close();
  });
}

const ipaddrRule = ref({
  ip: {
    required: true,
    validator: validateIpaddress,
    trigger: ['blur'],
  },
});

export {
  ipaddrRule,
  ipaddr,
  delay,
  ipaddrModalRef,
  delayModalRef,
  createColumns,
  submitDelay,
  submitIpaddr,
  ColumnDefault
};

