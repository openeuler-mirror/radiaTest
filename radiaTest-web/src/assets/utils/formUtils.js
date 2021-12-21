const macInput = (formValue) => {
  if ((formValue.value.mac.length - 1) % 3 === 2 &&
        formValue.value.mac.length < 18
  ) {
    formValue.value.mac =
            `${formValue.value.mac.substr(
              0,
              formValue.value.mac.length - 1
            ) 
            }:${ 
              formValue.value.mac.substr(
                formValue.value.mac.length - 1,
                1
              )}`;
  } else if (formValue.value.mac.length === 18) {
    formValue.value.mac = formValue.value.mac.substr(0, 17);
  }
  if (
    formValue.value.mac.substr(
      formValue.value.mac.length - 2,
      2
    ) === '::'
  ) {
    formValue.value.mac = formValue.value.mac.substr(
      0,
      formValue.value.mac.length - 2
    );
  }
};

const validateIpaddressCheckNull = (rule, value) => {
  if (!value) {
    return new Error('IP地址不可为空');
  } else if (
    !/^(([0-9]|[0-9]{2}|[0-9]{3})\.){3}([0-9]|[0-9]{2}|[0-9]{3})$/.test(
      value
    )
  ) {
    return new Error('IP地址不合法');
  } 
  return true;
};

const checkCIValid = (description, sshRules, basicRules) => {
  if (description === 'as the host of ci') {
    basicRules.value.listen = {
      required: true,
      message: 'worker的监听端口不可为空',
      trigger: ['blur'],
    };
    sshRules.value.password = {
      required: true,
      message: '必须设置SSH登陆密码',
      trigger: ['blur'],
    };
    sshRules.value.ip = {
      required: true,
      validator: validateIpaddressCheckNull,
      trigger: ['blur'],
    };
    sshRules.value.port = {
      required: true,
      message: '必须设置SSH端口',
      trigger: ['blur'],
    };
    sshRules.value.user = {
      required: true,
      message: '必须设置SSH登陆用户名',
      trigger: ['blur'],
    };
  } else if (description === 'used for ci') {
    sshRules.value.password = {
      required: true,
      message: '必须设置SSH登陆密码',
      trigger: ['blur'],
    };
    sshRules.value.ip = {
      required: true,
      validator: validateIpaddressCheckNull,
      trigger: ['blur'],
    };
  } else {
    basicRules.value.listen = {
      required: false,
    };
    sshRules.value.password = {
      required: false,
    };
    sshRules.value.ip = {
      required: false,
    };
  }
};

const getDesOptions = (formValue) => [
  {
    disabled: true,
    label: '自定义描述字段：',
    value: null,
  },
  {
    label: formValue.value.description,
    value: formValue.value.description,
  },
  {
    disabled: true,
    label: '预设描述字段：（CI非宿主机）',
    value: null,
  },
  {
    label: 'used for ci',
    value: 'used for ci',
  },
  {
    disabled: true,
    label: '预设描述字段：（CI宿主机）',
    value: null,
  },
  {
    label: 'as the host of ci',
    value: 'as the host of ci',
  },
];

const validateMac = (rule, value) => {
  if (!/^(([0-9A-Fa-f]{2}):){5}([0-9A-Fa-f]{2})$/.test(value)) {
    return new Error('MAC地址不合法');
  }
  return true;
};

const validateIpaddress = (rule, value) => {
  if (
    !/^(([0-9]|[0-9]{2}|[0-9]{3})\.){3}([0-9]|[0-9]{2}|[0-9]{3})$/.test(
      value
    ) &&
        value
  ) {
    return new Error('IP地址不合法');
  } 
  return true;
    
};

const validatePasswordSame = (rule, value, formValue) => {
  return value === formValue.value.password || (!value && !formValue.value.password);
};

const validateBmcPasswordSame = (rule, value, formValue) => {
  if (value !== formValue.value.bmc_password) {
    return new Error('两次密码不一致');
  } 
  return true;
};

const handleBmcPwdDisable = (formValue) => {
  if (!formValue.bmc_password && formValue.bmc_repassword) {
    formValue.bmc_repassword = null;
  }
  return !formValue.bmc_password;
};

const handleSshPwdDisable = (formValue) => {
  if (!formValue.password && formValue.repassword) {
    formValue.repassword = null;
  }
  return !formValue.password;
};

export {
  macInput,
  checkCIValid,
  getDesOptions,
  validateIpaddress,
  validateIpaddressCheckNull,
  validatePasswordSame,
  validateMac,
  validateBmcPasswordSame,
  handleBmcPwdDisable,
  handleSshPwdDisable
};
