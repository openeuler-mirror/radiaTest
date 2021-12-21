<template>
  <div>
    <n-form
      :label-width="40"
      :model="formValue"
      :rules="rules"
      :size="size"
      label-placement="top"
      ref="formRef"
    >
      <n-grid :cols="18">
        <n-gi :span="18">
          <n-form-item label="镜像URL地址" path="url">
            <n-input
              v-model:value="formValue.url"
              placeholder="镜像文件下载地址"
            />
          </n-form-item>
        </n-gi>
        <n-gi :span="18">
          <n-form-item
            label="kickstart文件路径"
            path="ks"
            v-show="thisFiletype === 'iso'"
          >
            <n-input
              v-model:value="formValue.ks"
              placeholder="kickstart文件路径"
            />
          </n-form-item>
        </n-gi>
        <n-gi :span="18">
          <n-form-item
            label="grub.efi路径"
            path="efi"
            v-show="thisFiletype === 'iso'"
          >
            <n-input
              v-model:value="formValue.efi"
              placeholder="grub.efi文件路径"
            />
          </n-form-item>
        </n-gi>
        <n-gi :span="18">
          <n-form-item
            label="安装源地址"
            path="location"
            v-show="thisFiletype === 'iso'"
          >
            <n-input
              v-model:value="formValue.location"
              placeholder="安装源地址"
            />
          </n-form-item>
        </n-gi>
        <n-gi :span="9">
          <n-form-item
            label="SSH用户名"
            path="user"
            v-show="thisFiletype === 'qcow2'"
          >
            <n-input
              v-model:value="formValue.user"
              placeholder="输入SSH用户名(默认root)"
              @keydown.enter.prevent
              style="width: 90%"
            />
          </n-form-item>
        </n-gi>
        <n-gi :span="9">
          <n-form-item
            label="SSH端口"
            path="port"
            v-show="thisFiletype === 'qcow2'"
          >
            <n-input
              v-model:value="formValue.port"
              placeholder="输入SSH端口(默认22)"
              @keydown.enter.prevent
              style="width: 90%"
            />
          </n-form-item>
        </n-gi>
        <n-gi :span="18">
          <n-form-item
            label="SSH密码"
            path="password"
            v-show="thisFiletype === 'qcow2'"
          >
            <n-input
              v-model:value="formValue.password"
              @keydown.enter.prevent
              type="password"
              show-password-on="mousedown"
              placeholder="请输入SSH密码"
              :style="{ width: '90%' }"
            />
          </n-form-item>
        </n-gi>
      </n-grid>
    </n-form>
  </div>
</template>

<script>
import { onUnmounted, defineComponent } from 'vue';

import validation from '@/assets/utils/validation.js';
import { createAjax } from '@/assets/CRUD/create';
import createForm from '@/views/milestone/modules/images/createForm.js';

export default defineComponent({
  setup(props, context) {
    onUnmounted(() => {
      createForm.clean();
    });

    return {
      ...createForm,
      handlePropsButtonClick: () => validation(createForm.formRef, context),
      post: () => {
        if (createForm.thisFiletype.value === 'iso') {
          createAjax.postForm('/v1/imirroring', createForm.formValue);
        } else {
          createAjax.postForm('/v1/qmirroring', createForm.formValue);
        }
        context.emit('close');
      },
    };
  },
});
</script>

<style scoped></style>
