import { h, ref, watch } from 'vue';
import axios from '@/axios';
import {
  getProductOpts,
  getVersionOpts,
  getMilestoneOpts,
  createSuiteOptions,
} from '@/assets/utils/getOpts.js';
import {
  createRepoOptions,
  createPmOptions,
  createVmOptions,
} from '@/assets/utils/getOpts';
import { NPopover } from 'naive-ui';

const formRef = ref(null);
const vmOptions = ref();
const pmOptions = ref();
const totalMachineCount = ref(0);
const isPmachine = ref(true);
const formValue = ref({
  name: '',
  product: undefined,
  version: undefined,
  milestone: undefined,
  suite: undefined,
  filetype: undefined,
  frame: undefined,
  framework: undefined,
  git_repo_id: undefined,
  select_mode: undefined,
  machine_list: [],
  strict_mode: false,
});
// const loading = ref(false);
// const warning = ref(false);

const productOpts = ref([]);
const versionOpts = ref([]);
const milestoneOpts = ref([]);
const frameworkOpts = ref([]);

// const suiteValidator = (rule, value) => {
//   // warning.value = false;
//   if (!value) {
//     return new Error('测试套不可为空');
//   }
//   // loading.value = true;
//   // return axios.validate(
//   //   '/v1/suite',
//   //   { name: formValue.value.suite },
//   //   loading,
//   //   warning,
//   //   true
//   // );
// };

const rules = {
  suite: {
    required: true,
    message: '测试套不可为空',
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
  },
  machine_list: {
    validator(rule, value) {
      if (value.length === 0) {
        return new Error('请选择机器');
      }
      if (
        formValue.value.strict_mode &&
        value.length < totalMachineCount.value
      ) {
        return new Error('严格模式下,选取机器数量应为要求数量');
      }
      return true;
    },
  },
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
  formValue.value = {
    name: '',
    product: undefined,
    version: undefined,
    milestone: undefined,
    suite: undefined,
    filetype: undefined,
    frame: undefined,
    framework: undefined,
    git_repo_id: undefined,
    select_mode: undefined,
    machine_list: [],
    strict_mode: false,
  };
  totalMachineCount.value = 0;
};
function getFramework() {
  axios.get('/v1/framework').then((res) => {
    frameworkOpts.value = res.data?.map((item) => ({
      label: item.name,
      value: String(item.id),
    }));
  });
}
const machineOptions = ref();
const getProductOptions = async () => {
  getProductOpts(productOpts);
  getFramework();
  vmOptions.value = await createVmOptions();
  pmOptions.value = await createPmOptions();
  machineOptions.value = pmOptions.value;
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
      getMilestoneOpts(milestoneOpts, formValue.value.version);
    }
  );
};
const repoOpts = ref();
async function frameworkChange(value) {
  repoOpts.value = await createRepoOptions({ framework_id: value });
}
const suiteOpts = ref();
async function repoChange(value) {
  suiteOpts.value = await createSuiteOptions({ git_repo_id: value });
}
function changeSuite(value) {
  const suite = suiteOpts.value.find((item) => item.value === value);
  totalMachineCount.value = suite.machineCount;
  console.log(suite);
  if (suite.machineType === 'kvm') {
    machineOptions.value = vmOptions.value;
    isPmachine.value = false;
  } else {
    machineOptions.value = pmOptions.value;
    isPmachine.value = true;
  }
  formValue.value.machine_list = [];
}
function selectPm(value) {
  if (value.length > totalMachineCount.value) {
    window.$message?.error('超出可选择数量');
  } else {
    formValue.value.machine_list = value;
  }
}
function renderSuiteOption({ node, option }) {
  return h(
    NPopover,
    { trigger: 'hover' },
    {
      trigger: () => node,
      default: () =>
        h('div', [
          h('p', `名称:${option.label}`),
          h('p', `节点类型:${option.machineType}`),
          h('p', `节点数:${option.machineCount}`),
        ]),
    }
  );
}

export default {
  suiteOpts,
  isPmachine,
  machineOptions,
  totalMachineCount,
  productOpts,
  versionOpts,
  repoOpts,
  milestoneOpts,
  frameworkOpts,
  formValue,
  selectPm,
  rules,
  formRef,
  validateFormData,
  clean,
  getProductOptions,
  activeProductWatcher,
  activeVersionWatcher,
  frameworkChange,
  repoChange,
  changeSuite,
  renderSuiteOption,
};
