<template>
  <span>
    <span class="account">{{ props.title }}</span>
    <span class="account">用户名/密码:</span>
    <span class="account">{{ accountInfo[props.title] }}</span>
  </span>
  <n-button
    class="account"
    v-if="!isShow[props.title]"
    type="success"
    text
    @click="handleShowClick(props.machineId, props.title)"
  >
    显示
  </n-button>
  <n-button class="account" v-if="isShow[props.title]" type="info" text @click="handleHideClick(props.title)">
    隐藏
  </n-button>
  <n-button
    v-if="isShow[props.title]"
    class="account"
    type="primary"
    text
    @click="
      () => {
        showModal = true;
      }
    "
  >
    修改
  </n-button>
  <n-modal v-model:show="showModal" :mask-closable="false">
    <n-dialog
      type="info"
      :title="`修改${props.title}信息`"
      negative-text="取消"
      positive-text="确认"
      @positive-click="submitCallback"
      @negative-click="cancelCallback"
      @close="cancelCallback"
    >
      <n-form :label-width="80" :model="formValue" ref="formRef" :rules="rules">
        <n-form-item label="用户名" path="user">
          <n-input :value="formValue.user" :disabled="true" />
        </n-form-item>
        <n-form-item label="旧密码" path="oldPassword">
          <n-input :value="formValue.oldPassword" :disabled="true" />
        </n-form-item>
        <n-form-item label="密码" path="password">
          <n-input
            v-model:value="formValue.password"
            placeholder="请输入密码"
            type="password"
            show-password-on="click"
          />
        </n-form-item>
        <n-form-item label="确认密码" path="rePassword">
          <n-input
            v-model:value="formValue.rePassword"
            placeholder="请再次输入密码"
            type="password"
            show-password-on="click"
          />
        </n-form-item>
      </n-form>
    </n-dialog>
  </n-modal>
</template>

<script setup>
import { onUnmounted } from 'vue';
import { getPmachineBmc, getPmachineSsh } from '@/api/get';
import { modifyPmachineBmc, modifyPmachineSsh } from '@/api/put';

const props = defineProps({
  title: String,
  machineId: Number
});

const showModal = ref(false);
const isShow = ref({
  SSH: false,
  BMC: false
});
const accountInfo = ref({
  SSH: '***** / *****',
  BMC: '***** / *****'
});
const formValue = ref({});
const formRef = ref();

function handleHideClick(target) {
  isShow.value[target] = false;
  formValue.value = {};
  accountInfo.value[target] = '***** / *****';
}

function handleShowClick(machineId, target) {
  if (target === 'BMC') {
    getPmachineBmc(props.machineId).then((res) => {
      accountInfo.value[target] = `${res.data.bmc_user} / ${res.data.bmc_password}`;
      formValue.value.user = res.data.bmc_user;
      formValue.value.oldPassword = res.data.bmc_password;
      isShow.value[target] = true;
    });
  } else if (target === 'SSH') {
    getPmachineSsh(props.machineId).then((res) => {
      accountInfo.value[target] = `${res.data.user} / ${res.data.password}`;
      formValue.value.user = res.data.user;
      formValue.value.oldPassword = res.data.password;
      isShow.value[target] = true;
    });
  }
}

function handleModifyClick(machineId, target) {
  formRef.value.validate((errors) => {
    if (!errors) {
      if (target === 'BMC') {
        modifyPmachineBmc(props.machineId, { bmc_password: formValue.value.password }).finally(() => {
          handleHideClick(target);
          showModal.value = false;
        });
      } else if (target === 'SSH') {
        modifyPmachineSsh(props.machineId, { password: formValue.value.password }).finally(() => {
          handleHideClick(target);
          showModal.value = false;
        });
      }
    } else {
      window.$message?.error('填写信息不符合要求');
    }
  });
}

function submitCallback() {
  handleModifyClick(props.machineId, props.title);
}
function cancelCallback() {
  showModal.value = false;
  formValue.value.password = null;
  formValue.value.rePassword = null;
}

const passwordValidator = (rule, value, oldPassword) => {
  if (!value) {
    return new Error('密码不可为空');
  } else if (value.length < 8) {
    return new Error('密码不可小于8位');
  } else if (value === oldPassword) {
    return new Error('新密码不可与旧密码相同');
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
    validator: (rule, value) => passwordValidator(rule, value, formValue.value.oldPassword)
  },
  rePassword: {
    trigger: ['blur', 'change'],
    required: true,
    validator: (rule, value) => rePasswordValidator(rule, value, formValue.value.password)
  }
};

onUnmounted(() => {
  formValue.value = {};
});
</script>

<style scoped>
.account {
  padding-right: 10px;
}
</style>
