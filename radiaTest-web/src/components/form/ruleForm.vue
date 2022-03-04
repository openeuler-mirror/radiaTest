<template>
  <modal-card
    :title="type === 'create' ? '创建规则' : '修改规则'"
    ref="createRuleModal"
    @validate="submitForm"
  >
    <template #form>
      <n-form :label-width="80" :model="formValue" :rules="rules" ref="formRef">
        <n-form-item label="名称" path="alias">
          <n-input v-model:value="formValue.alias" placeholder="请输入" />
        </n-form-item>
        <n-form-item label="路由" path="uri">
          <n-input v-model:value="formValue.uri" placeholder="请输入" />
        </n-form-item>
        <n-form-item label="请求方法" path="act">
          <n-select
            v-model:value="formValue.act"
            :options="methodList"
            placeholder="请选择"
          />
        </n-form-item>
        <n-form-item label="规则类型">
          <n-switch :rail-style="railStyle" v-model:value="formValue.eft">
            <template #checked>允许</template>
            <template #unchecked>拒绝</template>
          </n-switch>
        </n-form-item>
      </n-form>
    </template>
  </modal-card>
</template>
<script>
import modalCard from '@/components/CRUD/ModalCard.vue';
export default {
  components: {
    modalCard,
  },
  props: {
    type: {
      type: String,
      default: 'create'
    },
    formData: Array
  },
  methods: {
    show() {
      this.$nextTick(() => {
        if (this.type !== 'create') {
          this.formValue = this.formData;
          if (this.formValue.eft === 'allow') {
            this.formValue.eft = true;
          }
        }
        this.$refs.createRuleModal.show();
      });
    },
    submitForm() {
      this.$refs.formRef.validate((errors) => {
        if (!errors) {
          const data = JSON.parse(JSON.stringify(this.formValue));
          data.eft === true ? data.eft = 'allow' : data.eft = 'deny';
          this.$refs.createRuleModal.close();
          this.$emit('submitform', { data, type: this.type });
        } else {
          window.$message?.error('填写信息有误，请检查');
        }
      });
    },
  },
  data() {
    return {
      formValue: {
        alias: '',
        uri: '',
        act: null,
        eft: true,
      },
      methodList: [
        { label: 'get', value: 'get' },
        { label: 'post', value: 'post' },
        { label: 'delete', value: 'delete' },
        { label: 'put', value: 'put' },
      ],
      rules: {
        alias: {
          trigger: ['input', 'blur'],
          required: true,
          message: '请填写名称',
        },
        uri: {
          trigger: ['input', 'blur'],
          required: true,
          message: '请填写路由',
        },
        act: {
          trigger: ['change', 'blur'],
          required: true,
          message: '请选择请求方式',
        },
      },
    };
  },
  setup() {
    return {
      railStyle: ({ focused, checked }) => {
        const style = {};
        if (!checked) {
          style.background = '#d03050';
          if (focused) {
            style.boxShadow = '0 0 0 2px #d0305040';
          }
        } else {
          style.background = '#2080f0';
          if (focused) {
            style.boxShadow = '0 0 0 2px #2080f040';
          }
        }
        return style;
      }
    };
  }
};
</script>
