import { ref, watch } from 'vue';
import {
  macInput,
  checkCIValid,
  validateIpaddress,
  validateIpaddressCheckNull,
  validatePasswordSame,
  validateMac,
  validateBmcPasswordSame,
  handleBmcPwdDisable,
  handleSshPwdDisable,
} from '@/assets/utils/formUtils.js';

const size = ref('medium');

const frameRef = ref(null);
const tab = ref('basic');
const basicFormRef = ref(null);
const sshFormRef = ref(null);
const sshRePasswordRef = ref(null);
const bmcRePasswordRef = ref(null);

const basicFormValue = ref({
  frame: undefined,
  mac: undefined,
  listen: undefined,
  bmc_ip: undefined,
  bmc_user: undefined,
  bmc_password: undefined,
  bmc_repassword: undefined,
  description: undefined,
});

const sshFormValue = ref({
  ip: undefined,
  port: undefined,
  user: undefined,
  password: undefined,
  repassword: undefined,
});

const clean = () => {
  basicFormValue.value.frame = undefined;
  basicFormValue.value.mac = undefined;
  basicFormValue.value.listen = undefined;
  basicFormValue.value.bmc_ip = undefined;
  basicFormValue.value.bmc_user = undefined;
  basicFormValue.value.bmc_password = undefined;
  basicFormValue.value.bmc_repassword = undefined;
  basicFormValue.value.description = undefined;
  sshFormValue.value.ip = undefined;
  sshFormValue.value.port = undefined;
  sshFormValue.value.user = undefined;
  sshFormValue.value.password = undefined;
  sshFormValue.value.repassword = undefined;
  tab.value = 'basic';
};

const desOptions = [
  {
    label: '暂无',
    value: '暂无',
  },
  {
    label: 'used for ci',
    value: 'used for ci',
  },
  {
    label: 'as the host of ci',
    value: 'as the host of ci',
  },
];

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
  bmc_ip: {
    required: true,
    validator: validateIpaddressCheckNull,
    trigger: 'blur',
  },
  bmc_user: {
    required: true,
    message: 'BMC用户名不可为空',
    trigger: 'blur',
  },
  bmc_password: {
    required: true,
    message: 'BMC密码不可为空',
    trigger: 'blur',
  },
  bmc_repassword: {
    required: true,
    validator: (rule, value) => 
      validateBmcPasswordSame(rule, value, basicFormValue),
    trigger: ['blur', 'password-input'],
  },
});

const sshRules = ref({
  ip: {
    required: false,
    validator: validateIpaddress,
    trigger: ['blur'],
  },
  repassword: {
    validator: (rule, value) =>
      validatePasswordSame(rule, value, sshFormValue),
    message: '两次密码不一致',
    trigger: ['blur', 'password-input'],
  },
});

watch(
  () => basicFormValue.value.description,
  () => {
    checkCIValid(basicFormValue.value.description, sshRules, basicRules);
  }
);

const handleMacInput = () => {
  macInput(basicFormValue);
};

const handlePasswordInput = () => {
  if (sshFormValue.value.repassword) {
    sshRePasswordRef.value.validate({ trigger: 'password-input' });
  }
};

const handleBmcPasswordInput = () => {
  if (basicFormValue.value.bmc_repassword) {
    bmcRePasswordRef.value.validate({ trigger: 'password-input' });
  }
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
  frameRef,
  tab,
  basicFormRef,
  sshFormRef,
  sshRePasswordRef,
  bmcRePasswordRef,
  basicFormValue,
  sshFormValue,
  desOptions,
  basicRules,
  sshRules,
  clean,
  handleMacInput,
  handlePasswordInput,
  handleBmcPasswordInput,
  validateFormData,
  handleBmcPwdDisable,
  handleSshPwdDisable,
};

