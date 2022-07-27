import { ref } from 'vue';

const size = ref('medium');
const formRef = ref(null);
const productOpts = ref([]);
const versionOpts = ref([]);
const formValue = ref({
  name: undefined,
  product: undefined,
  product_id: undefined,
  type: undefined,
  start_time: undefined,
  end_time: undefined,
  is_sync: false,
  permission_type:undefined
});

const clean = () => {
  formValue.value = {
    name: undefined,
    product: undefined,
    product_id: undefined,
    type: undefined,
    start_time: undefined,
    end_time: undefined,
    is_sync: false,
    permission_type:undefined
  };
};

const rules = ref({
  product: {
    required: true,
    message: '产品名不可为空',
    trigger: ['blur'],
  },
  permission_type: {
    required: true,
    message: '请选择类型',
    trigger: ['change', 'blur'],
  },
  product_id: {
    required: true,
    message: '版本名不可为空',
    trigger: ['blur'],
  },
  type: {
    required: true,
    message: '里程碑类型不可为空',
    trigger: ['blur'],
  },
  end_time: {
    validator: (rule, value) => {
      if (!value) {
        return new Error('结束日期不可为空');
      }
      return true;
    },
    trigger: ['blur'],
  },
});

export default {
  size,
  rules,
  formRef,
  formValue,
  productOpts,
  versionOpts,
  clean,
};
