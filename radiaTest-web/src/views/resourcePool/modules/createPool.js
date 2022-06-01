import { ref } from 'vue';
import { createMachineGroup } from '@/api/post';
import { storage } from '@/assets/utils/storageUtils';
import { modifyMachineGroup } from '@/api/put';
import { isCreate, menuOption,refreshData } from './menu';
const createModalRef = ref(null);
const machinesFormRef = ref(null);
const createMachinesForm = ref({
  name: undefined,
  description: undefined,
  network_type: undefined,
  ip: undefined,
  messenger_listen: undefined,
  permission_type: undefined,
  websockify_listen: undefined,
  messenger_ip: undefined,
  websockify_ip:undefined,
});
const fileList = ref([]);
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
  let formData = new FormData();
  formData.append('creator_id', Number(storage.getValue('gitee_id')));
  formData.append('permission_type', createMachinesForm.value.permission_type.split('-')[0]);
  formData.append('org_id', storage.getValue('orgId'));
  formData.append('group_id', Number(createMachinesForm.value.permission_type.split('-')[1]));
  formData.append('name', createMachinesForm.value.name);
  formData.append('description', createMachinesForm.value.description);
  formData.append('network_type', createMachinesForm.value.network_type);
  formData.append('ip', createMachinesForm.value.ip);
  formData.append('messenger_ip', createMachinesForm.value.messenger_ip);
  formData.append('messenger_listen', createMachinesForm.value.messenger_listen);
  formData.append('websockify_ip', createMachinesForm.value.websockify_ip);
  formData.append('websockify_listen', createMachinesForm.value.websockify_listen);
  formData.append('ssl_cert', fileList.value[0]?.file);

  createMachineGroup(formData).then(() => {
    createModalRef.value.close();
    refreshData();
    createMachinesForm.value = {
      name: undefined,
      description: undefined,
      network_type: undefined,
      ip: undefined,
      listen: undefined,
      permission_type: undefined,
      websockify_listen: undefined,
      messenger_ip: undefined,
      websockify_ip: undefined
    };
    fileList.value = [];
  });
}
function modifyMachines() {
  let formData = new FormData();
  formData.append('name', createMachinesForm.value.name);
  formData.append('description', createMachinesForm.value.description);
  formData.append('network_type', createMachinesForm.value.network_type);
  formData.append('ip', createMachinesForm.value.ip);
  formData.append('messenger_ip', createMachinesForm.value.messenger_ip);
  formData.append('messenger_listen', createMachinesForm.value.messenger_listen);
  formData.append('websockify_ip', createMachinesForm.value.websockify_ip);
  formData.append('websockify_listen', createMachinesForm.value.websockify_listen);
  formData.append('ssl_cert', fileList.value[0]?.file);

  modifyMachineGroup(
    menuOption.id, 
    formData,
  ).then(() => {
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
    fileList.value = [];
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
function uploadFinish (options) {
  fileList.value = options;
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
  uploadFinish
};
