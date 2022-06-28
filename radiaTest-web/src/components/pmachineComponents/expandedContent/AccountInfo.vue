<template>
  <span>
      <span class="account">{{ title }}</span>
      <span class="account">用户名/密码:</span>
      <span class="account">{{ accountInfo[title] }}</span>  
  </span>
  <n-button 
    class="account"
    v-if="!isShow[title]" 
    type="success" 
    text
    @click="handleShowClick(machineId, title)"
  >
    显示
  </n-button>
  <n-button 
    class="account" 
    v-if="isShow[title]" 
    type="info" 
    text
    @click="handleHideClick(title)"
  >
    隐藏
  </n-button>
  <n-button 
    v-if="isShow[title]"
    class="account" 
    type="primary" 
    text
    @click="accountModalRef.show()"
  >
    修改
  </n-button>
  <modal-card
    :initY="100"
    :title="`修改${title}信息`"
    ref="accountModalRef"
    @validate="handleModifyClick(machineId, title)"
  >
    <template #form>
      <n-form 
        :label-width="80" 
        :model="formValue" 
        ref="formRef"
        :rules="rules"
      >
        <n-form-item label="用户名" path="user">
          <n-input 
            :value="formValue.user" 
            :disabled="true"
          />
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
    </template>
  </modal-card>
</template>

<script>
import { defineComponent, onUnmounted } from 'vue';
import secretInfo from '@/views/pmachine/modules/expandedContent/secretInfo.js';
import ModalCard from '@/components/CRUD/ModalCard';

export default defineComponent({
  components: {
    ModalCard,
  },
  props: {
    title: String,
    machineId: Number,
  },
  setup() {
    onUnmounted(() => {
      secretInfo.formValue.value = {};
    });
    return {
      ...secretInfo
    };
  },
});
</script>

<style scoped>
.account {
  padding-right: 10px;
}
</style>
