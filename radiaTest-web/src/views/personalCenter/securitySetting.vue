<template>
  <n-spin :show="showLoading" stroke="rgba(0, 47, 167, 1)">
    <card-page title="安全设置">
      <n-tabs type="line" animated>
        <n-tab-pane name="password" tab="修改密码">
          <n-form
            ref="passwordFormRef"
            :label-width="150"
            label-align="right"
            label-placement="left"
            :model="passwordModel"
            :rules="passwordFormRules"
            class="formWrap"
          >
            <n-form-item label="账户名" path="account">
              <div>{{ account }}</div>
            </n-form-item>
            <n-form-item label="旧密码" path="old_password">
              <n-input
                v-model:value="passwordModel.old_password"
                placeholder="请输入旧密码"
                type="password"
              ></n-input>
            </n-form-item>
            <n-form-item label="新密码" path="new_password" first>
              <n-input
                v-model:value="passwordModel.new_password"
                placeholder="请输入新密码且最小长度为8"
                type="password"
                @input="handlePasswordInput"
              ></n-input>
            </n-form-item>
            <n-form-item label="请重复新密码" path="re_new_password" ref="reNewPasswordRef" first>
              <n-input
                v-model:value="passwordModel.re_new_password"
                placeholder="请重复输入新密码"
                :disabled="!passwordModel.new_password"
                type="password"
              ></n-input>
            </n-form-item>
          </n-form>
          <div class="btnWrap">
            <n-space>
              <n-button size="large" type="error" ghost @click="resetPassword"> 重置 </n-button>
              <n-button size="large" type="primary" ghost @click="submitPassword"> 提交 </n-button>
            </n-space>
          </div>
        </n-tab-pane>
      </n-tabs>
    </card-page>
  </n-spin>
</template>

<script setup>
import { showLoading } from '@/assets/utils/loading';
import { storage } from '@/assets/utils/storageUtils';
import { changeAdminPassword } from '@/api/put';
import { useRouter } from 'vue-router';
const router = useRouter();
const account = ref('');
const passwordFormRef = ref(null);
const reNewPasswordRef = ref(null);
const passwordModel = ref({
  old_password: '',
  new_password: '',
  re_new_password: '',
});

const validateNewPassword = (rule, value) => {
  return value !== passwordModel.value.old_password;
};

const validatePasswordStartWith = (rule, value) => {
  return (
    !!passwordModel.value.new_password &&
    passwordModel.value.new_password.startsWith(value) &&
    passwordModel.value.new_password.length >= value.length
  );
};

const validatePasswordSame = (rule, value) => {
  return value === passwordModel.value.new_password;
};

const handlePasswordInput = () => {
  if (passwordModel.value.re_new_password) {
    reNewPasswordRef.value?.validate({ trigger: 'password-input' });
  }
};

const passwordFormRules = ref({
  old_password: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入旧密码',
  },
  new_password: [
    {
      required: true,
      trigger: ['blur', 'input'],
      min: 8,
      message: '请输入新密码且最小长度为8',
    },
    {
      validator: validateNewPassword,
      message: '新密码不能与旧密码相同',
      trigger: ['blur', 'input'],
    },
  ],
  re_new_password: [
    {
      required: true,
      trigger: ['blur', 'input'],
      message: '请重复输入新密码',
    },
    {
      validator: validatePasswordStartWith,
      message: '两次密码输入不一致',
      trigger: 'input',
    },
    {
      validator: validatePasswordSame,
      message: '两次密码输入不一致',
      trigger: ['blur', 'password-input'],
    },
  ],
});

const resetPassword = () => {
  passwordModel.value = {
    old_password: '',
    new_password: '',
    re_new_password: '',
  };
};

const submitPassword = () => {
  passwordFormRef.value?.validate(async (errors) => {
    if (!errors) {
      changeAdminPassword({
        account: account.value,
        old_password: passwordModel.value.old_password,
        new_password: passwordModel.value.new_password,
        re_new_password: passwordModel.value.re_new_password,
      })
        .then(() => {
          passwordModel.value = {
            old_password: '',
            new_password: '',
            re_new_password: '',
          };
          window.sessionStorage.clear();
          router.replace({
            name: 'task',
          });
        })
        .catch((err) => {
          window.$message?.error(err.data.error_msg || '未知错误');
        });
    }
  });
};

onMounted(() => {
  account.value = storage.getValue('account');
});
</script>

<style lang="less">
.formWrap {
  padding: 0 300px;
}

.btnWrap {
  display: flex;
  justify-content: center;
}
</style>
