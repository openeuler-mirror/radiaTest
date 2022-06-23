import { h, ref } from 'vue';
import { NSpace, NTag, NIcon, NButton, NTooltip, NGradientText } from 'naive-ui';
import { Construct } from '@vicons/ionicons5';
import { Locked } from '@vicons/carbon';
import { renderTooltip } from '@/assets/render/tooltip';

import PowerButton from '@/components/pmachineComponents/changeState/PowerButton';
import ConnectButton from '@/components/pmachineComponents/changeState/ConnectButton';
import InstallButton from '@/components/pmachineComponents/changeState/InstallButton';
import ExpandedCard from '@/components/pmachineComponents/ExpandedCard';
import { formatTime } from '@/assets/utils/dateFormatUtils';
import pmachineTable from './pmachineTable';
import { modifyPmachineDelayTime } from '@/api/put';
import { get } from '@/assets/CRUD/read';

const delayModalRef = ref();
const delay = ref({
  time: '',
  id: '',
});

const ColumnEndtime = ref({
  title: '释放时间',
  key: 'end_time',
  className: 'cols endtime',
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
  } 
});

const ColumnState = {
  title: '占用状态',
  key: 'state',
  className: 'state cols',
  render(row) {
    if (row.state === 'idle') {
      return h('span', null, '空闲');
    }
    if (row.locked) {
      return h(
        NIcon,
        {},
        {
          default: () => h(Locked),
        }
      );
    }
    return h('span', null, '占用');
  },
};

const ColumnDescription = {
  title: '使用说明',
  key: 'description',
  className: 'cols des',
  render(row) {
    if (row.description === 'as the host of ci') {
      return h(
        NTag,
        {
          type: 'info',
          round: true,
        },
        h(
          'div',
          {
            style: {
              width: '80px',
              textAlign: 'center',
            },
          },
          'host of CI'
        )
      );
    } else if (row.description === 'used for ci') {
      return h(
        NTag,
        {
          type: 'info',
          round: true,
        },
        h(
          'div',
          {
            style: {
              width: '80px',
              textAlign: 'center',
            },
          },
          'used for CI'
        )
      );
    }
    return h('div', {}, row.description);
  },
};

const ColumnExpand = {
  type: 'expand',
  renderExpand: (rowData) =>
    h(ExpandedCard, {
      data:rowData,
      IP: rowData.ip,
      machine_group_ip:rowData.machine_group.messenger_ip,
      messenger_listen:rowData.machine_group.messenger_listen
    }),
};

const getColumnOperation = (updateHandler) => {
  return {
    title: '操作',
    key: 'action',
    className: 'cols operation',
    render: (row) => {
      return h(NSpace, { class: 'operation' }, [
        h(PowerButton, {
          id: row.id,
          disabled: row.locked,
          status: row.status,
        }),
        h(ConnectButton, {
          disabled: row.locked,
          data: row,
        }),
        h(InstallButton, {
          id: row.id,
          disabled: row.locked,
        }),
        renderTooltip(
          h(
            NButton,
            {
              size: 'medium',
              type: 'warning',
              circle: true,
              disabled: row.state === 'occupied' || row.locked,
              onClick: () => updateHandler(row),
            },
            h(NIcon, { size: '20' }, h(Construct))
          ),
          '修改'
        ),
      ]);
    },
  };
};

const ColumnDefault = [
  {
    title: 'MAC地址',
    key: 'mac',
    className: 'cols mac',
  },
  {
    title: '架构',
    key: 'frame',
    className: 'cols frame',
  },
  {
    title: 'IP地址',
    key: 'ip',
    className: 'cols ip',
  },
  {
    title: 'BMC IP',
    key: 'bmc_ip',
    className: 'cols bmcip',
  },
  {
    title: '当前使用人',
    key: 'occupier',
    className: 'cols occupier',
  },
];

const createColumns = (updateHandler) => {
  return [
    ColumnExpand,
    ...ColumnDefault,
    ColumnState,
    ColumnDescription,
    ColumnEndtime.value,
    getColumnOperation(updateHandler),
  ];
};

function submitDelay() {
  modifyPmachineDelayTime(delay.value.id, {
    end_time: formatTime(delay.value.time, 'yyyy-MM-dd hh:mm:ss'),
  }).then(() => {
    delay.value.id = '';
    delay.value.time = '';
    get.list('/v1/pmachine', pmachineTable.totalData, pmachineTable.loading);
  });
}

export { 
  ColumnDefault, 
  createColumns, 
  ColumnEndtime, 
  submitDelay, 
  delay, 
  delayModalRef 
};

