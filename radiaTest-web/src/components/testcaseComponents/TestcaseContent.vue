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
          <!-- <modal-card
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
          </modal-card> -->
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

// import ModalCard from '@/components/CRUD/ModalCard.vue';
// import TestcaseUpdateContentForm from './TestcaseUpdateContentForm.vue';
import { Edit } from '@vicons/fa';
import caseModifyForm from '@/components/testcaseComponents/caseModifyForm.vue';
// import { createCaseReview } from '@/api/post';

export default defineComponent({
  components: {
    // TestcaseUpdateContentForm,
    // ModalCard,
    Edit,
    caseModifyForm,
  },
  props: {
    form: Object,
  },
  watch: {
    form: {
      handler(value) {
        console.log(1,value);
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
  methods:{
    // submit(value){
    //   createCaseReview({...value,case_detail_id:this.form.id}).then(()=>{
    //     this.$refs.updateModalRef.close();
    //   });
    // }
  },
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
