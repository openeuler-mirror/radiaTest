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
const frameOpts = ref([
  {
    label: 'aarch64',
    value: 'aarch64'
  },
  {
    label: 'x86_64',
    value: 'x86_64'
  },
]);

const formValue = ref({
  frame: undefined,
  product: undefined,
  version: undefined,
  milestone_id: undefined,
  cpu_mode: undefined,
  memory: 4096,
  capacity: null,
  sockets: 1,
  cores: 1,
  threads: 1,
  description: undefined,
  method: undefined,
});

const rules = ref({
  method: {
    required: true,
    message: '创建方法不可为空',
    trigger: ['blur'],
  },
  frame: {
    required: true,
    message: '架构不可为空',
    trigger: ['blur'],
  },
  product: {
    required: true,
    message: '产品名不可为空',
    trigger: ['blur'],
  },
  version: {
    required: true,
    message: '版本名不可为空',
    trigger: ['blur'],
  },
  milestone_id: {
    required: true,
    message: '里程碑不可为空',
    trigger: ['blur'],
  },
  description: {
    required: true,
    validator: (rule, value) => {
      if (!value) {
        return new Error('描述字段不可为空');
      }
      if (value.length < 10) {
        return new Error('描述字段长度不可低于10个字符');
      }
      return true;
    },
    trigger: ['blur'],
  },
});

const validateFormData = (context) => {
  formRef.value.validate((error) => {
    if (error) {
      window.$message?.error('请检查输入合法性');
    } else {
      context.emit('valid');
    }
  });
};

const validator = (value) => {
  return value > 0;
};

const clean = () => {
  formValue.value = {
    frame: undefined,
    product: undefined,
    version: undefined,
    milestone_id: undefined,
    cpu_mode: undefined,
    capacity: null,
    memory: 4096,
    sockets: 1,
    cores: 1,
    threads: 1,
    description: undefined,
    method: undefined,
  };
};

const getProductOptions = () => {
  getProductOpts(productOpts);
};

const activeMethodWatcher = () => {
  watch(
    () => formValue.value.method,
    () => {
      formValue.value.frame = null;
    }
  );
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

watch(() => formValue.value.method, () => {
  formValue.value.method === 'import'
    ? formValue.value.capacity = null
    : 0;
});

export default {
  size,
  productOpts,
  versionOpts,
  milestoneOpts,
  frameOpts,
  formValue,
  formRef,
  rules,
  validateFormData,
  validator,
  clean,
  getProductOptions,
  activeMethodWatcher,
  activeProductWatcher,
  activeVersionWatcher,
};

