<template>
  <n-list>
    <n-list-item>
      <n-thing>
        <template #header>用例描述 </template>
        <template #header-extra>
          <n-button text @click="() => updateModalRef.show()">
            <template #icon>
              <edit />
            </template>
          </n-button>
          <modal-card
            :initY="100"
            :initX="300"
            title="编辑文本用例内容"
            ref="updateModalRef"
            @validate="() => updateFormRef.handlePropsButtonClick()"
            @submit="updateFormRef.put()"
          >
            <template #form>
              <testcase-update-content-form
                ref="updateFormRef"
                :rowData="form"
                @valid="() => updateModalRef.submitCreateForm()"
                @close="
                  () => {
                    updateModalRef.close();
                    emitUpdateEvent();
                  }
                "
              />
            </template>
          </modal-card>
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

import ModalCard from '@/components/CRUD/ModalCard.vue';
import TestcaseUpdateContentForm from './TestcaseUpdateContentForm.vue';
import { Edit } from '@vicons/fa';

export default defineComponent({
  components: {
    TestcaseUpdateContentForm,
    ModalCard,
    Edit,
  },
  props: {
    form: Object,
  },
  setup(props, context) {
    const updateFormRef = ref(null);
    const updateModalRef = ref(null);

    return {
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
