<template>
  <ModalCard
    title="修改用例详情"
    ref="editModalRef"
    @validate="submitEdit"
    :initY="100"
    :initX="300"
  >
    <template #form>
      <n-form
        :label-width="40"
        :model="editFormValue"
        :rules="contentRules"
        :size="size"
        label-placement="top"
        ref="contentFormRef"
      >
        <n-grid :cols="18" :x-gap="24">
          <n-form-item-gi :span="18" label="标题" path="title">
            <n-input
              v-model:value="editFormValue.title"
              placeholder="请输入标题"
            />
          </n-form-item-gi>
          <n-form-item-gi :span="9" label="机器类型" path="machine_type">
            <n-select
              v-model:value="editFormValue.machine_type"
              :options="[
                { label: '物理机', value: 'physical' },
                { label: '虚拟机', value: 'kvm' },
              ]"
              placeholder="请准确描述此用例"
            />
          </n-form-item-gi>
          <n-form-item-gi :span="9" label="机器数量" >
            <n-input
              v-model:value="editFormValue.machine_num"
              type="number"
              placeholder="请准确描述此用例"
            />
          </n-form-item-gi>
          <n-form-item-gi :span="9" label="用例描述" path="case_description">
            <n-input
              v-model:value="editFormValue.case_description"
              type="textarea"
              :autosize="{
                minRows: 2,
              }"
              placeholder="请准确描述此用例"
            />
          </n-form-item-gi>
          <n-form-item-gi :span="9" label="预置条件" path="preset">
            <n-input
              v-model:value="editFormValue.preset"
              type="textarea"
              :autosize="{
                minRows: 2,
              }"
            />
          </n-form-item-gi>
          <n-form-item-gi :span="9" label="操作步骤" path="steps">
            <n-input
              v-model:value="editFormValue.steps"
              type="textarea"
              :autosize="{
                minRows: 4,
              }"
            />
          </n-form-item-gi>
          <n-form-item-gi :span="9" label="预期结果" path="expectation">
            <n-input
              v-model:value="editFormValue.expectation"
              type="textarea"
              :autosize="{
                minRows: 3,
              }"
            />
          </n-form-item-gi>
          <n-form-item-gi :span="18" label="描述">
            <n-input
              v-model:value="editFormValue.description"
              type="textarea"
              :autosize="{
                minRows: 2,
              }"
              placeholder="请准确描述本次修改"
            />
          </n-form-item-gi>
        </n-grid>
      </n-form>
    </template>
  </ModalCard>
</template>
<script>
import ModalCard from '@/components/CRUD/ModalCard.vue';
export default {
  components: {
    ModalCard,
  },
  props: ['formValue'],
  methods: {
    submitEdit() {
      this.$refs.contentFormRef.validate((errors) => {
        if (!errors) {
          this.$emit('submit',this.editFormValue);
        } else {
          window.$message.error('请检查输入');
        }
      });
    },
    close(){
      this.$refs.editModalRef.close();
    },
    show() {
      this.$refs.editModalRef.show();
    },
  },
  watch: {
    formValue: {
      handler() {
        this.editFormValue = this.formValue;
      },
      deep: true,
    },
  },
  data() {
    return {
      editFormValue: {
        machine_type: undefined,
        machine_num: undefined,
        description: undefined,
        steps: undefined,
        expectation: undefined,
        case_description: undefined,
        title: '',
        preset:''
      },
      contentRules: {
        title: {
          required: true,
          message: '机器类型不可为空',
          trigger: ['blur'],
        },
        machine_type: {
          required: true,
          message: '机器类型不可为空',
          trigger: ['blur'],
        },
        case_description: {
          required: true,
          message: '用例描述不可为空',
          trigger: ['blur'],
        },
        steps: {
          required: true,
          message: '用例步骤不可为空',
          trigger: ['blur'],
        },
        expectation: {
          required: true,
          message: '用例预期结果不可为空',
          trigger: ['blur'],
        },
      },
    };
  },
  setup() {},
};
</script>
