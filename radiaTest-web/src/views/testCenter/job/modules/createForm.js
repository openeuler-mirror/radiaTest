import { h, ref, watch } from 'vue';
import axios from '@/axios';
import {
  getProductOpts,
  getVersionOpts,
  getMilestoneOpts,
  createSuiteOptions,
} from '@/assets/utils/getOpts.js';
import { createRepoOptions } from '@/assets/utils/getOpts';
import { getVm, getPm,getMachineGroup } from '@/api/get';
import { NPopover } from 'naive-ui';
import { unkonwnErrorMsg } from '@/assets/utils/description';

const formRef = ref(null);
const vmOptions = ref([]);
const pmOptions = ref([]);
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
  select_mode: 'auto',
  machine_list: [],
  strict_mode: false,
  machine_group_id:undefined,
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
  machine_group_id:{
    required:true,
    message:'请选择机器组',
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
const checkedMachine = ref([]);
const clean = () => {
  checkedMachine.value = [];
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
    select_mode: 'auto',
    machine_list: [],
    strict_mode: false,
    machine_group_id:undefined
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
const machineOptions = ref([]);
const machineGroups = ref([]);
const getProductOptions = async () => {
  getProductOpts(productOpts);
  getFramework();
  machineOptions.value = pmOptions.value;
  getMachineGroup().then((res)=>{
    machineGroups.value = res.data?.map(item=>({label:item.name,value:String(item.id)}));
  });
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
const machineType = ref('pm');
async function frameworkChange(value) {
  repoOpts.value = await createRepoOptions({ framework_id: value });
}
const suiteOpts = ref();
async function repoChange(value) {
  suiteOpts.value = await createSuiteOptions({
    git_repo_id: value,
    usabled: true,
    auto: true,
  });
}
function changeSuite(value) {
  const suite = suiteOpts.value.find((item) => item.value === value);
  totalMachineCount.value = suite.machineCount;
  if (suite.machineType === 'kvm') {
    machineOptions.value = vmOptions.value;
    isPmachine.value = false;
    machineType.value = 'vm';
    checkedMachine.value = [];
  } else {
    machineOptions.value = pmOptions.value;
    isPmachine.value = true;
    machineType.value = 'pm';
    checkedMachine.value = [];
  }
  formValue.value.machine_list = [];
}

function selectPm(value) {
  console.log(value);
  if (value.length > totalMachineCount.value) {
    window.$message?.error('超出可选择数量');
  } else {
    formValue.value.machine_list = value;
    checkedMachine.value = value;
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
async function setMachineOptions(){
  try {
    const vmdata = await getVm({
      frame: formValue.value.frame,
      machine_purpose: 'run_job',
      machine_group_id:formValue.value.machine_group_id
    });
    vmOptions.value = vmdata.data;
    const pmdata = await getPm({
      frame: formValue.value.frame,
      machine_purpose: 'run_job',
      machine_group_id:formValue.value.machine_group_id
    });
    pmOptions.value = pmdata.data;
    if (machineType.value === 'pm') {
      machineOptions.value = pmOptions.value;
      checkedMachine.value = [];
    } else {
      machineOptions.value = vmOptions.value;
      checkedMachine.value = [];
    }
  } catch (err) {
    window.$message?.error(
      err.data?.error_msg || err.message || unkonwnErrorMsg
    );
  }
}
function changMachineGroup(value){
  if(value && formValue.value.frame){
    setMachineOptions();
  }
}
function frameChange(value) {
  if(value && formValue.value.machine_group_id){
    setMachineOptions();
  }
}
function renderText(values) {
  const result = [];
  if (values.length) {
    values.forEach((item) => {
      const element = machineOptions.value.find((i) => i.id === item);
      result.push(element?.ip);
    });
    return result.join(',');
  }
  return '';
}

export default {
  suiteOpts,
  machineType,
  isPmachine,
  machineOptions,
  totalMachineCount,
  productOpts,
  versionOpts,
  repoOpts,
  milestoneOpts,
  checkedMachine,
  frameworkOpts,
  formValue,
  selectPm,
  renderText,
  rules,
  formRef,
  validateFormData,
  clean,
  machineGroups,
  getProductOptions,
  activeProductWatcher,
  activeVersionWatcher,
  frameworkChange,
  repoChange,
  changeSuite,
  renderSuiteOption,
  frameChange,
  changMachineGroup
};
