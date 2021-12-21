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
      <n-grid :cols="18" :x-gap="24">
        <n-form-item-gi :span="9" label="产品" path="name">
          <n-auto-complete
            v-model:value="formValue.name"
            :options="nameOptions"
            #="{ handleInput, handleFocus, value }"
          >
            <n-input
              v-model:value="formValue.name"
              placeholder="输入版本所属产品名称"
              @input="handleInput"
              @focus="handleFocus"
              @keydown.enter.prevent
              style="width: 100%"
            />
          </n-auto-complete>
        </n-form-item-gi>
        <n-form-item-gi :span="9" label="版本" path="version">
          <n-input
            v-model:value="formValue.version"
            placeholder="输入待注册版本"
            @keydown.enter.prevent
          />
        </n-form-item-gi>
        <n-form-item-gi :span="18" label="描述" path="description">
          <n-input
            v-model:value="formValue.description"
            placeholder="产品版本的描述文本"
            @keydown.enter.prevent
          />
        </n-form-item-gi>
      </n-grid>
    </n-form>
  </div>
</template>

<script>
import { onUnmounted, defineComponent } from 'vue';

import validation from '@/assets/utils/validation.js';
import { createAjax } from '@/assets/CRUD/create';
import createForm from '@/views/product/modules/createForm.js';

export default defineComponent({
  setup(props, context) {
    onUnmounted(() => {
      createForm.clean();
    });

    return {
      ...createForm,
      handlePropsButtonClick: () => validation(createForm.formRef, context),
      post: () => {
        createAjax.postForm('/v1/product', createForm.formValue);
        context.emit('close');
      },
    };
  },
});
</script>

<style scoped></style>
