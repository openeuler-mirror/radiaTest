import { ref, watch } from 'vue';
import axios from '@/axios';
import {
  getProductOpts,
  getVersionOpts,
  getMilestoneOpts,
} from '@/assets/utils/getOpts.js';

const formRef = ref(null);
const formValue = ref({
  product: undefined,
  version: undefined,
  milestone: undefined,
  suite: undefined,
  filetype: undefined,
  frame: undefined,
});
const loading = ref(false);
const warning = ref(false);

const productOpts = ref([]);
const versionOpts = ref([]);
const milestoneOpts = ref([]);

const suiteValidator = (rule, value) => {
  warning.value = false;
  if (!value) {
    return new Error('测试套不可为空');
  }
  loading.value = true;
  return axios.validate(
    '/v1/suite',
    { name: formValue.value.suite },
    loading,
    warning,
    true,
  );
};

const rules = {
  suite: {
    required: true,
    validator: suiteValidator,
    trigger: ['blur'],
  },
  filetype: {
    required: true,
    message: '机器类型不可为空',
    trigger: ['blur'],
  },
  frame: {
    required: true,
    message: '架构不可为空',
    trigger: ['blur'],
  },
  milestone: {
    required: true,
    message: '请绑定里程碑',
    trigger: ['blur'],
  }
};

const validateFormData = (context) => {
  formRef.value.validate((error) => {
    if (error) {
      window.$message?.error('请检查输入合法性');
    } else {
      context.emit('valid');
    }
  });
};

const clean = () => {
  formValue.value.suite = undefined;
  formValue.value.frame = undefined;
  formValue.value.filetype = undefined;
  formValue.value.product = undefined;
  formValue.value.version = undefined;
  formValue.value.milestone = undefined;
};

const getProductOptions = () => {
  getProductOpts(productOpts);
};

const activeProductWatcher = () => {
  watch(
    () => formValue.value.product,
    () => {
      getVersionOpts(versionOpts, formValue.value.product);
    }
  );
};

const activeVersionWatcher = () => {
  watch(
    () => formValue.value.version,
    () => {
      getMilestoneOpts(
        milestoneOpts,
        formValue.value.version,
      );
    }
  );
};

export default {
  productOpts,
  versionOpts,
  milestoneOpts,
  formValue,
  rules,
  formRef,
  validateFormData,
  clean,
  getProductOptions,
  activeProductWatcher,
  activeVersionWatcher,
};
