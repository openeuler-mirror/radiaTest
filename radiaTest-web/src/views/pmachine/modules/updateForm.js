import { ref } from 'vue';
import {
  macInput,
  validateIpaddress,
  validateIpaddressCheckNull,
  validateMac,
} from '@/assets/utils/formUtils.js';

const size = ref('medium');

const machineId = ref(null);
const basicFrameRef = ref(null);
const tab = ref('basic');
const basicFormRef = ref(null);
const bmcFormRef = ref(null);
const sshFormRef = ref(null);

const basicFormValue = ref({
  frame: undefined,
  mac: undefined,
});

const bmcFormValue = ref({
  bmc_ip: undefined,
});

const sshFormValue = ref({
  ip: undefined,
  port: undefined,
});

const initData = (form) => {
  machineId.value = form.id;
  basicFormValue.value = {
    frame: form.frame,
    mac: form.mac,
  };
  bmcFormValue.value = {
    bmc_ip: form.bmc_ip,
  };
  sshFormValue.value = {
    ip: form.ip,
    port: form.port,
  };
};

const basicRules = ref({
  frame: {
    required: true,
    message: '架构不可为空',
    trigger: ['blur'],
  },
  mac: {
    required: true,
    validator: validateMac,
    trigger: 'blur',
  },
  
});

const bmcRules = ref({
  bmc_ip: {
    required: true,
    validator: validateIpaddressCheckNull,
    trigger: 'blur',
  },
});

const sshRules = ref({
  ip: {
    required: false,
    validator: validateIpaddress,
    trigger: ['blur'],
  },
});

const handleMacInput = () => {
  macInput(basicFormValue);
};

const validateFormData = (context) => {
  basicFormRef.value.validate((basicError) => {
    sshFormRef.value.validate((sshError) => {
      if (basicError || sshError) {
        window.$message?.error('请检查输入合法性');
      } else {
        context.emit('valid');
      }
    });
  });
};

export default {
  size,
  machineId,
  basicFrameRef,
  tab,
  basicFormRef,
  bmcFormRef,
  sshFormRef,
  basicFormValue,
  bmcFormValue,
  sshFormValue,
  basicRules,
  bmcRules,
  sshRules,
  handleMacInput,
  validateFormData,
  initData,
};

