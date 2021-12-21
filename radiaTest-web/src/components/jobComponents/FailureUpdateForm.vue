<template>
  <n-form
    inline
    :label-width="80"
    :model="formValue"
    :rules="rules"
    size="medium"
    ref="formRef"
  >
    <n-grid :cols="12" :x-gap="12">
      <n-form-item-gi :span="12" label="问题类型" path="fail_type">
        <n-input
          v-model:value="formValue.fail_type"
          placeholder="若确认为非问题请填写‘非问题’"
          filterable
        />
      </n-form-item-gi>
      <n-gi :span="12">
        <n-form-item label="问题描述" path="details">
          <n-input
            type="textarea"
            :autosize="{
              minRows: 5,
            }"
            v-model:value="formValue.details"
            placeholder="若确认为问题，请对问题进行描述"
            filterable
          />
        </n-form-item>
      </n-gi>
    </n-grid>
  </n-form>
</template>

<script>
import { ref, toRefs, onMounted, defineComponent } from 'vue';

import { updateAjax } from '@/assets/CRUD/update';

export default defineComponent({
  props: {
    data: Object,
  },
  setup(props, context) {
    const formRef = ref(null);
    const formValue = ref({
      fail_type: undefined,
      details: undefined,
    });
    const { data } = toRefs(props);

    onMounted(() => {
      formValue.value.fail_type = data.value.fail_type;
      formValue.value.details = data.value.details;
    });

    const validateFormData = () => {
      formRef.value.validate((error) => {
        if (error) {
          window.$message?.error('请检查输入合法性');
        } else {
          context.emit('valid');
        }
      });
    };

    return {
      formRef,
      formValue,
      handlePropsButtonClick: () => validateFormData(),
      put: () => {
        updateAjax.putFormEmitClose(
          '/v1/analyzed',
          ref({
            id: data.value.id,
            fail_type: formValue.value.fail_type,
            details: formValue.value.details,
          }),
          context
        );
      },
    };
  },
});
</script>
