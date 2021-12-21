import { h, ref } from 'vue';
import { NSpace, NTag, NIcon, NButton } from 'naive-ui';
import { Construct } from '@vicons/ionicons5';
import { renderTooltip } from '@/assets/render/tooltip';

import PowerButton from '@/components/pmachineComponents/changeState/PowerButton';
import ConnectButton from '@/components/pmachineComponents/changeState/ConnectButton';
import InstallButton from '@/components/pmachineComponents/changeState/InstallButton';
import ExpandedCard from '@/components/pmachineComponents/ExpandedCard';

const ColumnEndtime = ref({
  title: '释放时间',
  key: 'end_time',
  className: 'cols endtime',
  sorter: true,
  sortOrder: false,
});

const ColumnState = {
  title: '占用状态',
  key: 'state',
  className: 'state cols',
  render(row) {
    if (row.state === 'idle') {
      return h('span', null, '空闲');
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
      SSHUSER: rowData.user,
      SSHPORT: rowData.port,
      SSHPASSWORD: rowData.password,
      LISTEN: rowData.listen,
      DESCRIPTION: rowData.description,
      IP: rowData.ip,
    }),
};

const getColumnOperation = (updateHandler) => {
  return {
    title: '操作',
    key: 'action',
    className: 'cols operation',
    render: (row) => {
      return h(
        NSpace,
        {
          class: 'operation',
        },
        [
          h(PowerButton, {
            id: row.id,
            status: row.status,
          }),
          h(ConnectButton, {
            data: {
              id: row.id,
              state: row.state,
              ip: row.ip,
              mac: row.mac,
              end_time: row.end_time,
              listen: row.listen,
              description: row.description,
            },
          }),
          h(InstallButton, {
            id: row.id,
          }),
          renderTooltip(
            h(
              NButton,
              {
                size: 'medium',
                type: 'warning',
                circle: true,
                disabled: row.state === 'occupied',
                onClick: () => updateHandler(row),
              },
              h(NIcon, { size: '20' }, h(Construct))
            ),
            '修改'
          ),
        ]
      );
    }
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

export {
  createColumns,
  ColumnEndtime,
};

