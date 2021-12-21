import { ref, watch } from 'vue';
import {
  getProductOpts,
  getVersionOpts,
  getMilestoneOpts,
} from '@/assets/utils/getOpts.js';

const size = ref('medium');

const formRef = ref(null);
const productOpts = ref([]);
const versionOpts = ref([]);
const milestoneOpts = ref([]);

const formValue = ref({
  product: undefined,
  version: undefined,
  milestone_id: undefined
});

const clean = () => {
  formValue.value.product = undefined;
  formValue.value.version = undefined;
  formValue.value.milestone_id = undefined;
};

const rules = ref({
  milestone_id: {
    required: true,
    message: '里程碑不可为空',
    trigger: 'blur',
  },
});

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

const validateFormData = (context) => {
  formRef.value.validate((error) => {
    if (error) {
      window.$message?.error('请检查输入合法性');
    } else {
      context.emit('valid');
    }
  });
};

export default {
  size,
  formValue,
  formRef,
  rules,
  productOpts,
  versionOpts,
  milestoneOpts,
  clean,
  validateFormData,
  getProductOptions,
  activeProductWatcher,
  activeVersionWatcher,
};
