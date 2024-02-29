<template>
  <n-list>
    <n-list-item>
      <n-thing>
        <template #header>用例描述 </template>
        <template #header-extra>
          <n-button :disabled="true" text @click="() => updateModalRef.show()">
            <template #icon>
              <edit />
            </template>
          </n-button>
          <caseModifyForm @submit="submit" ref="updateModalRef" :formValue="formValue" />
        </template>
        <pre>{{ form.description }}</pre>
      </n-thing>
    </n-list-item>
    <n-list-item>
      <n-thing content-indented>
        <template #header>预置条件</template>
        <pre>{{ form.preset }}</pre>
      </n-thing>
    </n-list-item>
    <n-list-item>
      <n-thing content-indented>
        <template #header>操作步骤</template>
      </n-thing>
      <pre>{{ form.steps }}</pre>
    </n-list-item>
    <n-list-item>
      <n-thing content-indented>
        <template #header>预期结果</template>
      </n-thing>
      <pre>{{ form.expection }}</pre>
    </n-list-item>
  </n-list>
</template>

<script>
import { ref, defineComponent } from 'vue';

import { Edit } from '@vicons/fa';
import caseModifyForm from '@/components/testcaseComponents/caseModifyForm.vue';

export default defineComponent({
  components: {
    Edit,
    caseModifyForm,
  },
  props: {
    form: Object,
  },
  watch: {
    form: {
      handler() {
        this.formValue = ref({
          machine_type: undefined,
          machine_num: undefined,
          description: undefined,
          steps: this.form.steps,
          preset: this.form.preset,
          expectation: this.form.expection,
          case_description: this.form.description,
          title: '',
        });
      },
      deep: true,
    },
  },
  methods: {},
  setup(props, context) {
    const updateFormRef = ref(null);
    const updateModalRef = ref(null);
    const formValue = ref({});
    return {
      formValue,
      updateFormRef,
      updateModalRef,
      emitUpdateEvent() {
        context.emit('update');
      },
    };
  },
});
</script>

<style scoped></style>
