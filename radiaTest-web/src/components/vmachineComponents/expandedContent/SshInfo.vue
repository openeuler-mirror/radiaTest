<template>
  <span>
      <span class="account">SSH</span>
      <span class="account">用户名/密码:</span>
      <span class="account">{{ accountInfo }}</span>  
  </span>
  <n-button 
    class="account"
    v-if="!isShow" 
    type="success" 
    text
    @click="handleShowClick()"
  >
    显示
  </n-button>
  <n-button 
    class="account" 
    v-if="isShow" 
    type="info" 
    text
    @click="handleHideClick()"
  >
    隐藏
  </n-button>
  <n-button 
    v-if="isShow"
    class="account" 
    type="primary" 
    text
    @click="accountModalRef.show()"
  >
    修改
  </n-button>
  <modal-card
    :initY="100"
    :title="`修改SSH信息`"
    ref="accountModalRef"
    @validate="handleModifyClick()"
  >
    <template #form>
      <n-form :label-width="80" :model="formValue">
        <n-form-item label="用户名" path="user">
          <n-input v-model:value="formValue.user" placeholder="请输入用户名" />
        </n-form-item>
        <n-form-item label="密码" path="password">
          <n-input
            v-model:value="formValue.password"
            placeholder="请输入密码"
            type="password"
          />
        </n-form-item>
      </n-form>
    </template>
  </modal-card>
</template>

<script>
import { ref, defineComponent } from 'vue';
import { getVmachineSsh } from '@/api/get';
import { modifyVmachineSsh } from '@/api/put';
import ModalCard from '@/components/CRUD/ModalCard';

export default defineComponent({
  components: {
    ModalCard,
  },
  props: {
    machineId: Number,
  },
  setup(props) {
    const isShow = ref(false);
    const accountInfo = ref('***** / *****');
    const formValue = ref({});
    const accountModalRef = ref();
    function handleHideClick() {
      isShow.value = false;
      formValue.value = {};
      accountInfo.value = '***** / *****';
    }
    return {
      isShow,
      formValue,
      accountInfo,
      accountModalRef,
      handleHideClick,
      handleShowClick() {
        getVmachineSsh(props.machineId).then((res) => {
          accountInfo.value = `${res.data.user} / ${res.data.password}`;
          formValue.value.user = res.data.user;
          formValue.value.password = res.data.password;
          isShow.value = true;
        });
      },
      handleModifyClick() {
        modifyVmachineSsh(props.machineId, formValue.value).finally(() => {
          handleHideClick();
          accountModalRef.value.close();
        });
      },
    };
  },
});
</script>

<style scoped>
.account {
  padding-right: 10px;
}
</style>
