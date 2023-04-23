import { ref, watch, h } from 'vue';
import { NTooltip } from 'naive-ui';
import { getProductOpts, getVersionOpts, getMilestoneOpts } from '@/assets/utils/getOpts.js';
import { getPm } from '@/api/get';
import { ColumnDefault } from '@/views/pmachine/modules/pmachineTableColumns';
import router from '@/router';

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
  }
]);

const frameRule = {
  trigger: ['blur', 'change'],
  validator(rule, value) {
    let count = 0;
    formValue.value.frame_number.forEach((item) => {
      if (item.frame === value) {
        count++;
      }
    });
    if (count > 1) {
      return new Error('不可选择重复架构');
    }
    return true;
  }
};

const createFrameAndNumber = () => {
  return {
    frame: 'aarch64',
    machine_num: 1
  };
};

const changeFrameAndNumber = () => {
  if (formValue.value.frame_number?.length > 1) {
    formValue.value.pm_select_mode = 'auto';
    checkedPm.value = null;
    formValue.value.pmachine_id = null;
    formValue.value.pmachine_name = null;
  } else if (formValue.value.frame_number?.length === 1) {
    checkedPm.value = null;
    formValue.value.pmachine_id = null;
    formValue.value.pmachine_name = null;
    getPm({
      machine_purpose: 'create_vmachine',
      frame: formValue.value.frame_number[0].frame,
      machine_group_id: window.atob(router.currentRoute.value.params.machineId)
    }).then((res) => {
      pmData.value = res.data;
    });
  }
};

const formValue = ref({
  frame_number: [],
  pm_select_mode: undefined,
  product: undefined,
  version: undefined,
  milestone_id: undefined,
  cpu_mode: undefined,
  memory: 4096,
  capacity: 50,
  sockets: 1,
  cores: 1,
  threads: 1,
  description: undefined,
  method: undefined,
  pmachine_id: undefined,
  permission_type: undefined
});
const checkedPm = ref();

const rules = ref({
  method: {
    required: true,
    message: '创建方法不可为空',
    trigger: ['blur']
  },
  permission_type: {
    required: true,
    message: '请选择类型',
    trigger: ['change', 'blur']
  },
  frame_number: {
    required: true,
    type: 'array',
    message: '虚拟机架构及数量不可为空',
    trigger: ['blur', 'change']
  },
  product: {
    required: true,
    message: '产品名不可为空',
    trigger: ['blur']
  },
  version: {
    required: true,
    message: '版本名不可为空',
    trigger: ['blur']
  },
  pm_select_mode: {
    required: true,
    message: '请选择物理机机器调度策略',
    trigger: ['blur', 'change']
  },
  capacity: {
    message: '单架构磁盘容量不可超过500GiB',
    validator(rule, value) {
      let flag = true;
      formValue.value.frame_number.forEach((item) => {
        if (item.machine_num * value > 500) {
          flag = false;
        }
      });
      return flag;
    },
    trigger: ['change', 'blur']
  },
  pmachine_id: {
    required: true,
    message: '物理机不可为空'
  },
  milestone_id: {
    required: true,
    message: '里程碑不可为空',
    trigger: ['blur']
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
    trigger: ['blur']
  }
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
  checkedPm.value = '';
  formValue.value = {
    frame_number: [],
    product: undefined,
    version: undefined,
    milestone_id: undefined,
    cpu_mode: undefined,
    capacity: 50,
    pm_select_mode: undefined,
    pmachine_id: undefined,
    memory: 4096,
    sockets: 1,
    cores: 1,
    threads: 1,
    description: undefined,
    method: undefined,
    permission_type: undefined
  };
};
const pmData = ref();
const getProductOptions = () => {
  getProductOpts(productOpts);
};

const activeMethodWatcher = () => {
  watch(
    () => formValue.value.method,
    () => {
      formValue.value.frame_number = [];
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
      getMilestoneOpts(milestoneOpts, formValue.value.version);
    }
  );
};

watch(
  () => formValue.value.method,
  () => {
    formValue.value.method === 'import' ? (formValue.value.capacity = null) : (formValue.value.capacity = 50);
  }
);
function renderOption({ node, option }) {
  return h(NTooltip, null, {
    trigger: () => node,
    default: () => {
      return `ip:${option.info.ip}<br/>label:${option.label}`;
    }
  });
}

const pmcolumns = [
  {
    type: 'selection'
  },
  ...ColumnDefault
].map((item) => {
  if (item.type) {
    return item;
  }
  return { key: item.key, title: item.title };
});
const pagination = {
  pageSize: 5
};
function handleCheck(check) {
  checkedPm.value = [check?.pop()];
  [formValue.value.pmachine_id] = checkedPm.value;
  formValue.value.pmachine_name = pmData.value.find((item) => item.id === formValue.value.pmachine_id).ip;
}
export default {
  checkedPm,
  size,
  pmcolumns,
  pagination,
  pmData,
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
  renderOption,
  handleCheck,
  getProductOptions,
  activeMethodWatcher,
  activeProductWatcher,
  activeVersionWatcher,
  createFrameAndNumber,
  frameRule,
  changeFrameAndNumber
};
