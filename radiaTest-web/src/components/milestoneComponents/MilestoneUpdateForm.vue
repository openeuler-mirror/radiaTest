<template>
  <n-form :label-width="40" :model="formValue" :rules="rules" :size="size" label-placement="top" ref="formRef">
    <n-grid :cols="18" :x-gap="24">
      <n-form-item-gi :span="18" label="里程碑名" path="name">
        <n-input
          v-model:value="formValue.name"
          placeholder="若不填写将会根据产品版本和类型自动生成里程碑名"
          clearable
        />
      </n-form-item-gi>
      <n-form-item-gi :span="9" label="开始时间" path="start_time">
        <n-date-picker
          type="date"
          v-model:value="formValue.start_time"
          placeholder="选择版本的开始日期"
          style="width: 100%"
        />
      </n-form-item-gi>
      <n-form-item-gi :span="9" label="结束时间" path="end_time">
        <n-date-picker
          type="date"
          v-model:value="formValue.end_time"
          placeholder="选择版本的开始日期"
          style="width: 100%"
        />
      </n-form-item-gi>
    </n-grid>
  </n-form>
</template>

<script>
import { ref, computed, onMounted, defineComponent } from 'vue';
import { useStore } from 'vuex';

import { any2standard } from '@/assets/utils/dateFormatUtils.js';
import validation from '@/assets/utils/validation.js';
import updateAjax from '@/assets/CRUD/update/updateAjax.js';
import updateForm from '@/views/versionManagement/milestone/modules/updateForm.js';

export default defineComponent({
  setup(props, context) {
    const store = useStore();

    onMounted(() => {
      updateForm.formValue.value = computed(() => store.getters.getRowData).value;
    });

    return {
      ...updateForm,
      handlePropsButtonClick: () => validation(updateForm.formRef, context),
      put: () => {
        const start = any2standard(updateForm.formValue.value.start_time);
        const end = any2standard(updateForm.formValue.value.end_time);
        const data = ref({
          id: updateForm.formValue.value.id,
          name: updateForm.formValue.value.name,
          start_time: start,
          end_time: end
        });
        updateAjax.putForm('/v2/milestone', data);
        context.emit('close');
      }
    };
  }
});
</script>

<style scoped></style>
