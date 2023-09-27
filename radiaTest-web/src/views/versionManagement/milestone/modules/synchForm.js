import { ref } from 'vue';

const size = ref('medium');
const formRef = ref(null);
const productOpts = ref([]);
const versionOpts = ref([]);
const milestoneNameActive = ref(true);
const milestoneOpts = ref([]);
const formValue = ref({
  product: undefined,
  product_id: undefined,
  permission_type: undefined,
  milestone_list:[]
});

const clean = () => {
  formValue.value = {
    product: undefined,
    product_id: undefined,
    permission_type: undefined,
    milestone_list: []
  };
};

const rules = ref({
  product: {
    required: true,
    message: '产品名不可为空',
    trigger: ['blur']
  },
  permission_type: {
    required: true,
    message: '请选择类型',
    trigger: ['change', 'blur']
  },
  product_id: {
    required: true,
    message: '版本名不可为空',
    trigger: ['blur']
  },
 
   milestone_list: {
    equired: true,
    message: '版本名不可为空',
    validator: (rule, value) => {
      if (!value.length) {
        return new Error('代码仓不可为空');
      }
      return true;
    },
    trigger: ['change','blur']
  }
});

const milestoneNameActiveChange = (value) => {
  if (value) {
    formValue.value.name = null;
  }
};

export default {
  size,
  rules,
  formRef,
  formValue,
  productOpts,
  versionOpts,
  milestoneNameActive,
  clean,
  milestoneNameActiveChange,
  milestoneOpts
};
