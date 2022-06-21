import { ref, h } from 'vue';
import {
  AirplayFilled,
  AutoAwesomeMosaicOutlined,
  CircleSharp,
} from '@vicons/material';
import { EditOutlined } from '@vicons/antd';
import { 
  Delete28Regular,
  ArrowSync20Regular,
  CalendarCheckmark24Regular,
  TextDescription20Regular 
} from '@vicons/fluent';
import { Add } from '@vicons/ionicons5';
import { NButton, NIcon } from 'naive-ui';
import { showCreateModal,createMachinesForm } from './createPool';
import { getMachineGroup,getRootCert } from '@/api/get';
import { Socket } from '@/socket';
import config from '@/assets/config/settings';
import router from '@/router';
import {deleteMachineGroup} from '@/api/delete';
import { activeTab } from './switch';

const isCreate = ref(false);
function renderIcon(icon) {
  return () =>
    h(NIcon, null, {
      default: () => h(icon),
    });
}
const menuOptions = ref([
  {
    label: 'radiaTest资源池',
    key: 'pool',
    isLeaf: false,
  },
]);
const expandeds = ref(['pool']);
const socket = new Socket(`${config.websocketProtocol}://${config.serverPath}/machine_group`);
const selectKey = ref('');
function renderPrefix({ option }) {
  return h(
    NIcon,
    {
      color: option.color || 'rgba(0, 47, 167, 1)',
      class: option.color ? `bounceIn ${option.key}` : '',
    },
    {
      default: () => {
        if (option.key === 'pool') {
          return h(AutoAwesomeMosaicOutlined);
        } else if (option.key.indexOf('server') !== -1) {
          return h(CircleSharp);
        } else if (option.key.startsWith('description')) {
          return h(TextDescription20Regular);
        }
        return h(AirplayFilled);
      },
    }
  );
}
const x = ref(0);
const y = ref(0);
const showDropdown = ref();
const options = ref([
  {
    label: '机器组证书检查',
    key: 'check',
    icon: renderIcon(CalendarCheckmark24Regular),
  },
  {
    label: '机器组证书更新',
    key: 'refresh',
    disabled: true,
    icon: renderIcon(ArrowSync20Regular),
  },
  {
    label: '机器组信息修改',
    key: 'edit',
    icon: renderIcon(EditOutlined),
  },
  {
    label: '机器组删除',
    key: 'delete',
    icon: renderIcon(Delete28Regular),
  },
]);
function handleExpandKey(keys) {
  if (expandeds.value.length >= 2) {
    expandeds.value.splice(1, 1, keys.pop());
  } else {
    expandeds.value = keys;
  }
}
let menuOption;
function nodeProps({ option }) {
  return {
    onClick() {
      if (option.value) {
        const keys = JSON.parse(JSON.stringify(expandeds.value));
        handleExpandKey([...keys, option.key]);
        activeTab.value = 'pmachine';
        router.push({
          name: 'pmachine',
          params: {
            machineId: option.value,
          },
        });
      }
    },
    onContextmenu(e) {
      if (option.value) {
        showDropdown.value = true;
        x.value = e.clientX;
        y.value = e.clientY;
        menuOption = option.info;
      }
      e.preventDefault();
    },
  };
}
function getTimeDiff(diffTime) {
  if (diffTime > 24 * 60 * 60 * 1000) {
    return '>1天';
  } else if (diffTime > 60 * 60 * 1000) {
    return `${Math.floor(diffTime / (60 * 60 * 1000))}小时前`;
  } else if (diffTime > 60 * 1000) {
    return `${Math.floor(diffTime / (60 * 1000))}分钟前`;
  } else if (diffTime > 30 * 1000) {
    return '30秒前';
  }
  return '刚刚';
}
function refreshData(){
  menuOptions.value = [
    {
      label: 'radiaTest资源池',
      key: 'pool',
      isLeaf: false,
    },
  ];
  expandeds.value = ['pool'];
  if(router.currentRoute.value.name !== 'resourcePool'){
    expandeds.value.push(router.currentRoute.value.params.machineId);
  }
}
function handleSelect(key) {
  if(key === 'check'){
    window.location.href = `https://${menuOption.messenger_ip}:${menuOption.messenger_listen}/api/v1/ca-check`;
  }else if(key === 'edit'){
    createMachinesForm.value = menuOption;
    showCreateModal();
    isCreate.value = false;
  }else if(key === 'delete'){
    deleteMachineGroup(menuOption.id).then(()=>{
      refreshData();
    });
  }
  showDropdown.value = false;
}
function handleClickoutside() {
  showDropdown.value = false;
}
function renderSuffix({ option }) {
  if (option.key === 'pool') {
    return h(
      NIcon,
      {
        color: 'rgba(0, 47, 167, 1)',
        onClick: (e) => {
          e.stopPropagation();
          showCreateModal();
          isCreate.value = true;
        },
      },
      {
        default: () => h(Add),
      }
    );
  } else if (option.suffix) {
    return h(NButton, { type: 'primary', text: true }, option.suffix);
  }
  return '';
}
function handleTreeLoad (node) {
  return new Promise((resolve, reject) => {
    getMachineGroup()
      .then((res) => {
        node.children = res.data.map((item) => ({
          label: item.name,
          key: String(item.id),
          value: item.id,
          info:item,
          suffix: item.ip,
          children: [
            {
              label: item.description,
              key: `description-${item.id}`
            },
            {
              label: 'messenger服务',
              key: `messenger_server-${item.id}`,
              color: item.messenger_alive ? 'green' : 'red',
              suffix: getTimeDiff(
                Date.now() - new Date(item.messenger_last_heartbeat)
              ),
            },
            {
              label: 'pxe服务',
              key: `pxe_server-${item.id}`,
              color: item.pxe_alive ? 'green' : 'red',
              suffix: getTimeDiff(
                Date.now() - new Date(item.pxe_last_heartbeat)
              ),
            },
            {
              label: 'dhcp服务 ',
              key: `dhcp_server-${item.id}`,
              color: item.dhcp_alive ? 'green' : 'red',
              suffix: getTimeDiff(
                Date.now() - new Date(item.dhcp_last_heartbeat)
              ),
            },
          ],
        }));
        resolve(res);
      })
      .catch((err) => {
        reject(err);
      });
  });
}
const contentHeight = ref(0);
const contentWidth = ref(0);

function handleSelectKey(keys) {
  const key = keys.pop();
  if (key.indexOf('server') === -1) {
    selectKey.value = key;
  }
}

function handleDownloadCert() {
  return new Promise((resolve, reject) => {
    getRootCert()
      .then((res) => {
        const blob = new Blob([res]);
        const link = document.createElement('a');
        link.download = 'radiatest.cacert.pem';
        link.style.display = 'none';
        link.href = URL.createObjectURL(blob);
        document.body.appendChild(link);
        link.click();
        URL.revokeObjectURL(link.href);
        document.body.removeChild(link);
        resolve();
      })
      .catch((err) => {
        reject(err);
      });
  });
}

export {
  expandeds,
  selectKey,
  contentHeight,
  contentWidth,
  x,
  y,
  showDropdown,
  menuOptions,
  menuOption,
  handleTreeLoad,
  options,
  nodeProps,
  handleSelect,
  handleClickoutside,
  renderPrefix,
  renderSuffix,
  handleExpandKey,
  socket,
  handleSelectKey,
  getTimeDiff,
  isCreate,
  refreshData,
  handleDownloadCert
};
