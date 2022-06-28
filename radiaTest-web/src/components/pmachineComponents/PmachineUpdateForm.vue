<template>
  <div v-show="tab === 'basic'">
    <n-form
      :label-width="40"
      :model="basicFormValue"
      :rules="basicRules"
      :size="size"
      label-placement="top"
      ref="basicFormRef"
    >
      <n-grid :cols="24" :x-gap="24">
        <n-form-item-gi
          :span="12"
          label="架构"
          path="frame"
          ref="basicFrameRef"
        >
          <n-select
            v-model:value="basicFormValue.frame"
            :options="[
              { label: 'aarch64', value: 'aarch64' },
              { label: 'x86_64', value: 'x86_64' },
            ]"
            placeholder="选择架构"
            filterable
          />
        </n-form-item-gi>
        <n-form-item-gi :span="12" label="MAC地址" path="mac">
          <n-input
            v-model:value="basicFormValue.mac"
            placeholder="输入物理机MAC地址"
            @input="handleMacInput"
            @keydown.enter.prevent
          />
        </n-form-item-gi>
      </n-grid>
    </n-form>
  </div>
  <div v-show="tab === 'bmc'">
    <n-form
      :label-width="40"
      :model="bmcFormValue"
      :rules="bmcRules"
      :size="size"
      label-placement="top"
      ref="bmcFormRef"
    >
      <n-grid :cols="24" :x-gap="24">
        <n-form-item-gi :span="12" label="BMC IP" path="bmc_ip">
          <n-input
            v-model:value="bmcFormValue.bmc_ip"
            placeholder="输入BMC的IP地址"
            @keydown.enter.prevent
          />
        </n-form-item-gi>
        <n-form-item-gi :span="12" label="BMC 用户名">
          <n-input
            v-model:value="bmcFormValue.bmc_user"
            placeholder="输入BMC用户名"
            @keydown.enter.prevent          
          />
        </n-form-item-gi>
      </n-grid>
      <n-form-item label="BMC 密码">
        <n-input
          v-model:value="bmcFormValue.bmc_password"
          @keydown.enter.prevent
          type="password"
          show-password-on="click"
          placeholder="请输入"
        />
      </n-form-item>
    </n-form>
  </div>
  <div v-show="tab === 'ssh'">
    <n-form
      :label-width="40"
      :model="sshFormValue"
      :rules="sshRules"
      :size="size"
      label-placement="top"
      ref="sshFormRef"
    >
      <n-grid :cols="24" :x-gap="24">
        <n-form-item-gi :span="6" label="SSH IP" path="ip">
          <n-input
            v-model:value="sshFormValue.ip"
            placeholder="请输入"
            @keydown.enter.prevent
          />
        </n-form-item-gi>
        <n-form-item-gi :span="6" label="SSH 端口" path="port">
          <n-input
            v-model:value="sshFormValue.port"
            placeholder="请输入"
            @keydown.enter.prevent
          />
        </n-form-item-gi>
        <n-form-item-gi :span="12" label="SSH 用户名">
          <n-input
            v-model:value="sshFormValue.user"
            placeholder="请输入"
            @keydown.enter.prevent
          />
        </n-form-item-gi>
      </n-grid>
      <n-form-item label="输入密码">
        <n-input
          v-model:value="sshFormValue.password"
          @keydown.enter.prevent
          type="password"
          show-password-on="click"
          placeholder="请输入"
        />
      </n-form-item>
    </n-form>
  </div>
</template>

<script>
import { ref, computed, onMounted, defineComponent } from 'vue';
import { useStore } from 'vuex';

import updateAjax from '@/assets/CRUD/update/updateAjax.js';
import updateForm from '@/views/pmachine/modules/updateForm.js';

export default defineComponent({
  setup(props, context) {
    const store = useStore();

    onMounted(() => {
      const formValue = computed(() => store.getters.getRowData);
      updateForm.initData(formValue.value);
    });

    return {
      ...updateForm,
      handlePropsButtonClick: () => updateForm.validateFormData(context),
      changeTabs: (tabValue) => {
        updateForm.tab.value = tabValue;
      },
      put: () => {
        const formValue = ref({
          id: updateForm.machineId.value,
          ...updateForm.basicFormValue.value,
          ...updateForm.bmcFormValue.value,
          ...updateForm.sshFormValue.value,
        });
        updateAjax.putForm('/v1/pmachine', formValue);
        context.emit('close');
      },
    };
  },
});
</script>

<style scoped></style>
