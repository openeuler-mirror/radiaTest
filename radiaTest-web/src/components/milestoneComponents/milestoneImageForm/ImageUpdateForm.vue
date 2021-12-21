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
import { updateAjax } from '@/assets/CRUD/update';
import updateForm from '@/views/milestone/modules/images/updateForm.js';

export default defineComponent({
  setup(props, context) {
    onUnmounted(() => {
      updateForm.clean();
    });

    return {
      ...updateForm,
      handlePropsButtonClick: () => validation(updateForm.formRef, context),
      put: () => {
        if (updateForm.thisFiletype.value === 'iso') {
          updateAjax.putForm('/v1/imirroring', updateForm.formValue);
        } else {
          updateAjax.putForm('/v1/qmirroring', updateForm.formValue);
        }
        context.emit('close');
      },
    };
  },
});
</script>

<style scoped></style>
