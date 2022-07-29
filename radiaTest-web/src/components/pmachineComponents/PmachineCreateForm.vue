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
        <n-form-item-gi :span="6" label="架构" path="frame" ref="frameRef">
          <n-select
            v-model:value="basicFormValue.frame"
            :options="[
              { label: 'aarch64', value: 'aarch64' },
              { label: 'x86_64', value: 'x86_64' },
            ]"
            placeholder="选择物理机架构"
            filterable
          />
        </n-form-item-gi>
        <n-form-item-gi :span="6" label="MAC地址" path="mac">
          <n-input
            v-model:value="basicFormValue.mac"
            placeholder="输入物理机MAC地址"
            @input="handleMacInput"
            @keydown.enter.prevent
          />
        </n-form-item-gi>
        <n-form-item-gi :span="6" label="类型" path="permission_type">
          <n-cascader
            v-model:value="basicFormValue.permission_type"
            placeholder="请选择"
            :options="typeOptions"
            check-strategy="child"
            remote
            :on-load="handleLoad"
          />
        </n-form-item-gi>
        <n-gi :span="6">
          <n-form-item
            label="worker监听端口"
            path="listen"
            v-show="basicFormValue.description === 'as the host of ci'"
          >
            <n-input
              v-model:value="basicFormValue.listen"
              placeholder="设定连接worker服务的端口"
              @keydown.enter.prevent
            />
          </n-form-item>
        </n-gi>
        <n-form-item-gi :span="12" label="BMC IP" path="bmc_ip">
          <n-input
            v-model:value="basicFormValue.bmc_ip"
            placeholder="输入BMC的IP地址"
            @keydown.enter.prevent
          />
        </n-form-item-gi>
        <n-form-item-gi :span="12" label="BMC 用户名" path="bmc_user">
          <n-input
            v-model:value="basicFormValue.bmc_user"
            placeholder="输入BMC用户名"
            @keydown.enter.prevent
            :style="{ width: '80%' }"
          />
        </n-form-item-gi>
      </n-grid>
      <n-form-item label="BMC 密码" path="bmc_password">
        <n-input
          v-model:value="basicFormValue.bmc_password"
          @keydown.enter.prevent
          @input="handleBmcPasswordInput"
          type="password"
          show-password-on="click"
          placeholder="请输入BMC密码"
          :style="{ width: '90%' }"
        />
      </n-form-item>
      <n-form-item
        label="重复密码"
        path="bmc_repassword"
        ref="bmcRePasswordRef"
      >
        <n-input
          :disabled="handleBmcPwdDisable(basicFormValue)"
          v-model:value="basicFormValue.bmc_repassword"
          type="password"
          show-password-on="click"
          @keydown.enter.prevent
          placeholder="重复密码以确认无误"
          :style="{ width: '90%' }"
        />
      </n-form-item>
      <n-form-item
        label="描述（除宿主机和测试机之外用途请选暂无）"
        path="description"
      >
        <n-select
          v-model:value="basicFormValue.description"
          :options="desOptions"
          placeholder="CI宿主机请选as the host of ci; CI测试机请选used for ci"
        >
        </n-select>
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
        <n-form-item-gi :span="6" label="IP地址" path="ip">
          <n-input
            v-model:value="sshFormValue.ip"
            placeholder="输入物理机SSH IP"
            @keydown.enter.prevent
            :style="{ width: '96%' }"
          />
        </n-form-item-gi>
        <n-form-item-gi :span="6" label="端口" path="port">
          <n-input
            v-model:value="sshFormValue.port"
            placeholder="输入SSH端口"
            @keydown.enter.prevent
            :style="{ width: '92%' }"
          />
        </n-form-item-gi>
        <n-form-item-gi :span="6" label="用户名" path="user">
          <n-input
            v-model:value="sshFormValue.user"
            placeholder="输入用户名"
            @keydown.enter.prevent
          />
        </n-form-item-gi>
      </n-grid>
      <n-form-item label="设置密码" path="password">
        <n-input
          v-model:value="sshFormValue.password"
          @keydown.enter.prevent
          @input="handlePasswordInput"
          type="password"
          show-password-on="click"
          placeholder="请输入SSH登陆密码"
          :style="{ width: '90%' }"
        />
      </n-form-item>
      <n-form-item label="重复密码" path="repassword" ref="rePasswordRef">
        <n-input
          :disabled="handleSshPwdDisable(sshFormValue)"
          v-model:value="sshFormValue.repassword"
          type="password"
          show-password-on="click"
          @keydown.enter.prevent
          placeholder="请输入"
          :style="{ width: '90%' }"
        />
      </n-form-item>
    </n-form>
  </div>
</template>

<script>
import { ref, onUnmounted, defineComponent } from 'vue';

import { storage } from '@/assets/utils/storageUtils';
import { createAjax } from '@/assets/CRUD/create';
import createForm from '@/views/pmachine/modules/createForm.js';
import { removeKey } from '@/assets/utils/objectUtils.js';
import extendForm from '@/views/versionManagement/product/modules/createForm.js';
import router from '@/router';
export default defineComponent({
  setup(props, context) {
    onUnmounted(() => {
      createForm.clean();
    });

    return {
      ...createForm,
      typeOptions: extendForm.typeOptions,
      handleLoad: extendForm.handleLoad,
      handlePropsButtonClick: () => createForm.validateFormData(context),
      changeTabs: (tabValue) => {
        createForm.tab.value = tabValue;
      },
      post: () => {
        const basic = removeKey(
          createForm.basicFormValue.value,
          'bmc_repassword'
        );
        const ssh = removeKey(createForm.sshFormValue.value, 'repassword');
        const formValue = ref(undefined);
        if (
          basic.description !== 'as the host of ci' &&
          basic.description !== 'used for ci'
        ) {
          formValue.value = {
            ...basic,
            ...ssh,
          };
        } else {
          formValue.value = {
            ...basic,
            ...ssh,
            occupier: storage.getValue('gitee_name'),
          };
        }
        createAjax.postForm('/v1/pmachine', {
          value: {
            ...formValue.value,
            permission_type: createForm.basicFormValue.value.permission_type.split('-')[0],
            creator_id: Number(storage.getValue('gitee_id')),
            org_id: storage.getValue('orgId'),
            group_id: Number(createForm.basicFormValue.value.permission_type.split('-')[1]),
            machine_group_id:window.atob(router.currentRoute.value.params.machineId)
          }
        });
        context.emit('close');
      },
    };
  },
});
</script>

<style scoped></style>
