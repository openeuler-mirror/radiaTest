import { ref } from 'vue';
import { getPmachineBmc, getPmachineSsh } from '@/api/get';
import { modifyPmachineBmc, modifyPmachineSsh } from '@/api/put';

const isShow = ref({
  SSH: false,
  BMC: false,
});
const accountInfo = ref({
  SSH: '***** / *****',
  BMC: '***** / *****',
});
const formValue = ref({});
const formRef = ref();
const accountModalRef = ref();

const passwordValidator = (rule, value) => {
  if (!value) {
    return new Error('密码不可为空');
  } else if (value.length < 8) {
    return new Error('密码不可小于8位');
  }
  return true;
};
const rePasswordValidator = (rule, value, password) => {
  if (!value) {
    return new Error('请再次输入待修改密码');
  } else if (value !== password) {
    return new Error('两次输入的密码不一致');
  }
  return true;
};

const rules = {
  password: {
    trigger: ['blur', 'change'],
    required: true,
    validator: (rule, value) => passwordValidator(rule, value),
  },
  rePassword: {
    trigger: ['blur', 'change'],
    required: true,
    validator: (rule, value) => rePasswordValidator(rule, value, formValue.value.password),
  }
};

function handleHideClick(target) {
  isShow.value[target] = false;
  formValue.value[target] = {};
  accountInfo.value[target] = '***** / *****';
}

function handleShowClick(machineId, target) {
  if (target === 'BMC') {
    getPmachineBmc(machineId).then((res) => {
      accountInfo.value[target] = `${res.data.bmc_user} / ${res.data.bmc_password}`;
      formValue.value.user = res.data.bmc_user;
      formValue.value.password = res.data.bmc_password;
      isShow.value[target] = true;
    });
  } else if (target === 'SSH') {
    getPmachineSsh(machineId).then((res) => {
      accountInfo.value[target] = `${res.data.user} / ${res.data.password}`;
      formValue.value.user = res.data.user;
      formValue.value.password = res.data.password;
      isShow.value[target] = true;
    });
  }
}

function handleModifyClick(machineId, target) {
  formRef.value.validate((errors) => {
    if (!errors) {
      if (target === 'BMC') {
        modifyPmachineBmc(machineId, { password: formValue.value.password }).finally(() => {
          handleHideClick(target);
          accountModalRef.value.close();
        });
      } else if (target === 'SSH') {
        modifyPmachineSsh(machineId, { password: formValue.value.password }).finally(() => {
          handleHideClick(target);
          accountModalRef.value.close();
        });
      }
    } else {
      window.$message?.error('填写信息不符合要求');
    }
  });    
}

export default {
  isShow,
  accountInfo,
  formValue,
  formRef,
  accountModalRef,
  handleHideClick,
  handleModifyClick,
  handleShowClick,
  rules,
};

