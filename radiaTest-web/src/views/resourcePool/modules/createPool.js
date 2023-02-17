import { ref } from 'vue';
import { storage } from '@/assets/utils/storageUtils';
import { createMachineGroup } from '@/api/post';
import { modifyMachineGroup } from '@/api/put';
import { isCreate, menuOption,refreshData } from './menu';
const createModalRef = ref(null);
const machinesFormRef = ref(null);
const createMachinesForm = ref({
  name: undefined,
  description: undefined,
  network_type: 'LAN',
  ip: undefined,
  messenger_listen: undefined,
  permission_type: undefined,
  websockify_listen: undefined,
  messenger_ip: undefined,
  websockify_ip:undefined,
});
const syncWebsockifyIP = ref(true);
const syncMessengerIP = ref(true);
const machinesRules = {
  name: {
    required: true,
    message: '名称必填',
    trigger: ['blur', 'input'],
  },
  description: {
    required: true,
    message: '描述必填',
    trigger: ['blur', 'input'],
  },
  network_type: {
    required: true,
    message: '网络类型必填',
    trigger: ['blur', 'input'],
  },
  ip: {
    message: 'IP有误',
    validator(rule, value) {
      const reg = /^(\d{1,2}|1\d\d|2[0-4]\d|25[0-5])\.(\d{1,2}|1\d\d|2[0-4]\d|25[0-5])\.(\d{1,2}|1\d\d|2[0-4]\d|25[0-5])\.(\d{1,2}|1\d\d|2[0-4]\d|25[0-5])$/;
      return reg.test(value);
    },
    trigger: ['blur', 'input'],
  },
  messenger_ip: {
    message: 'IP有误',
    validator (rule, value) {
      const reg = /^(\d{1,2}|1\d\d|2[0-4]\d|25[0-5])\.(\d{1,2}|1\d\d|2[0-4]\d|25[0-5])\.(\d{1,2}|1\d\d|2[0-4]\d|25[0-5])\.(\d{1,2}|1\d\d|2[0-4]\d|25[0-5])$/;
      return reg.test(value);
    },
    trigger: ['blur', 'input'],
  },
  websockify_ip: {
    message: 'IP有误',
    validator (rule, value) {
      const reg = /^(\d{1,2}|1\d\d|2[0-4]\d|25[0-5])\.(\d{1,2}|1\d\d|2[0-4]\d|25[0-5])\.(\d{1,2}|1\d\d|2[0-4]\d|25[0-5])\.(\d{1,2}|1\d\d|2[0-4]\d|25[0-5])$/;
      return reg.test(value);
    },
    trigger: ['blur', 'input'],
  },
  permission_type: {
    message: '请选择类型',
    required: true,
    trigger: ['blur', 'input'],
  },
  messenger_listen: {
    message: '端口必填',
    validator (rule, value) {
      return value > 0;
    },
    trigger: ['blur', 'input'],
  },
  websockify_listen: {
    message: '端口必填',
    validator(rule, value) {
      return value > 0;
    },
    trigger: ['blur', 'input'],
  }
};
function changeValue (value) {
  if (syncMessengerIP.value) {
    createMachinesForm.value.messenger_ip = value;
  }
  if (syncWebsockifyIP.value) {
    createMachinesForm.value.websockify_ip = value;
  }
}
function showCreateModal() {
  createModalRef.value.show();
}
function createMachines() {
  createMachineGroup({
    ...createMachinesForm.value,
    permission_type: createMachinesForm.value.permission_type.split('-')[0],
    creator_id: String(storage.getValue('user_id')),
    org_id: storage.getValue('orgId'),
    group_id: Number(createMachinesForm.value.permission_type.split('-')[1]),
  }).then(() => {
    createModalRef.value.close();
    refreshData();
    createMachinesForm.value = {
      name: undefined,
      description: undefined,
      network_type: 'LAN',
      ip: undefined,
      listen: undefined,
      permission_type: undefined,
      websockify_listen: undefined,
      messenger_ip: undefined,
      websockify_ip: undefined
    };
  });
}
function modifyMachines() {
  const formData = JSON.parse(JSON.stringify(createMachinesForm.value));
  delete formData.permission_type;
  modifyMachineGroup(menuOption.id, { ...formData }).then(() => {
    createModalRef.value.close();
    refreshData();
    createMachinesForm.value = {
      name: undefined,
      description: undefined,
      network_type: undefined,
      ip: undefined,
      messenger_listen: undefined,
      permission_type: undefined,
      websockify_listen:undefined
    };
  });
}
function submitCreateForm() {
  machinesFormRef.value.validate((error) => {
    if (!error) {
      if (isCreate.value) {
        createMachines();
      } else {
        modifyMachines();
      }
    } else {
      window.$message?.error('请检查输入');
    }
  });
}

export {
  machinesRules,
  syncMessengerIP,
  syncWebsockifyIP,
  createMachinesForm,
  createModalRef,
  showCreateModal,
  machinesFormRef,
  submitCreateForm,
  changeValue,
};
