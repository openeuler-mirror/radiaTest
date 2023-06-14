<template>
  <div>
    <n-form :label-width="40" :model="formValue" :rules="rules" :size="size" label-placement="top" ref="formRef">
      <n-grid :cols="18" :x-gap="24">
        <n-form-item-gi :span="6" label="产品" path="name">
          <n-input
            v-model:value="formValue.name"
            placeholder="输入版本所属产品名称"
            @input="handleInput"
            @focus="handleFocus"
            @keydown.enter.prevent
            clearable
            style="width: 100%"
          />
        </n-form-item-gi>
        <n-form-item-gi :span="6" label="版本" path="version">
          <n-input v-model:value="formValue.version" placeholder="输入待注册版本" @keydown.enter.prevent />
        </n-form-item-gi>
        <n-form-item-gi :span="6" label="类型" path="permission_type">
          <n-cascader
            v-model:value="formValue.permission_type"
            placeholder="请选择"
            :options="typeOptions"
            check-strategy="child"
            remote
            :on-load="handleLoad"
          />
        </n-form-item-gi>
        <n-form-item-gi :span="6" label="版本类型" path="version_type">
          <n-select
            v-model:value="formValue.version_type"
            :options="[
              {
                label: 'LTS',
                value: 'LTS'
              },
              {
                label: 'LTS-SPx',
                value: 'LTS-SPx'
              },
              {
                label: '创新版本',
                value: 'INNOVATION'
              }
            ]"
            placeholder="选择里版本类型"
          />
        </n-form-item-gi>
        <n-form-item-gi :span="6" label="是否强制管控">
          <n-switch v-model:value="formValue.is_forced_check">
            <template #checked> 是 </template>
            <template #unchecked> 否 </template>
          </n-switch>
        </n-form-item-gi>
        <n-form-item-gi :span="6" label="是否ebs构建">
          <n-switch v-model:value="formValue.built_by_ebs">
            <template #checked> 是 </template>
            <template #unchecked> 否 </template>
          </n-switch>
        </n-form-item-gi>
        <n-form-item-gi :span="18" label="描述" path="description">
          <n-input v-model:value="formValue.description" placeholder="产品版本的描述文本" @keydown.enter.prevent />
        </n-form-item-gi>
      </n-grid>
    </n-form>
  </div>
</template>

<script>
import { onUnmounted, defineComponent } from 'vue';

import validation from '@/assets/utils/validation.js';
import { createAjax } from '@/assets/CRUD/create';
import createForm from '@/views/versionManagement/product/modules/createForm.js';
import { storage } from '@/assets/utils/storageUtils';

export default defineComponent({
  setup(props, context) {
    onUnmounted(() => {
      createForm.clean();
    });

    return {
      ...createForm,
      handlePropsButtonClick: () => validation(createForm.formRef, context),
      post: () => {
        const formData = {
          value: {
            ...createForm.formValue.value,
            permission_type: createForm.formValue.value.permission_type.split('-')[0],
            creator_id: storage.getValue('user_id'),
            org_id: storage.getValue('loginOrgId'),
            group_id: Number(createForm.formValue.value.permission_type.split('-')[1])
          }
        };
        createAjax.postForm('/v1/product', formData).then(() => {
          context.emit('close');
        });
      }
    };
  }
});
</script>

<style scoped></style>
