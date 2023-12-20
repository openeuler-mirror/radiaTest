import { ref, watch, h } from 'vue';
import { NTooltip, NIcon } from 'naive-ui';
import { getProductOpts, getVersionOpts, getMilestoneOpts } from '@/assets/utils/getOpts.js';
import { getPm } from '@/api/get';
import { ColumnDefault } from '@/views/pmachine/modules/pmachineTableColumns';
import router from '@/router';
import { Add } from '@vicons/ionicons5';
import axios from '@/axios';
import { storage } from '@/assets/utils/storageUtils';
import { unkonwnErrorMsg } from '@/assets/utils/description';
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
    machine_num: 1,
    cpu_mode: 'host-passthrough',
    memory: 4096,
    capacity: formValue.value.method === 'import' ? null : 50,
    pm_select_mode: 'auto',
    sockets: 1,
    cores: 1,
    threads: 1
  };
};

const changeFrameAndNumber = (value, item) => {
  if (value > 1) {
    item.pm_select_mode = 'auto';
    checkedPm.value = null;
    item.pmachine_id = null;
    item.pmachine_name = null;
  } else if (value === 1) {
    checkedPm.value = null;
    item.pmachine_id = null;
    item.pmachine_name = null;
    // getPm({
    //   machine_purpose: 'create_vmachine',
    //   frame: item.frame,
    //   machine_group_id: window.atob(router.currentRoute.value.params.machineId)
    // }).then((res) => {
    //   pmData.value = res.data;
    // });
  }
};
const getPmList = (item) => {
  getPm({
    machine_purpose: 'create_vmachine',
    frame: item.frame,
    machine_group_id: window.atob(router.currentRoute.value.params.machineId)
  }).then((res) => {
    pmData.value = res.data;
  });
};
const handleUpdatePmSelectMode = (show, item) => {
  if (show && item.machine_num === 1) {
    getPmList(item);
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
  permission_type: undefined,
  version_types: []
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
  },
  version_types: {
    required: true,
    type: 'array',
    message: '虚拟机架构及数量不可为空',
    trigger: ['change', 'blur']
  }
});

const validateFormData = async (context) => {
  formRef.value.validate((error) => {
    if (error) {
      window.$message?.error('请检查输入合法性');
    } else {
      let machineses = [];
      formValue.value.version_types.forEach((item) => {
        item.machines.forEach((mItem) => {
          mItem.frame_number = [{ frame: mItem.frame, machine_num: mItem.machine_num }];
          mItem.milestone_id = item.basicInfo.milestone_id;
          mItem.product = item.basicInfo.product;
          mItem.version = item.basicInfo.version;
          mItem.method = item.basicInfo.method;
          mItem.description = mItem.selfdescription || formValue.value.description;
          mItem.permission_type = formValue.value.permission_type.split('-')[0];
          mItem.creator_id = storage.getValue('user_id');
          mItem.org_id = storage.getValue('loginOrgId');
          mItem.machine_group_id = window.atob(router.currentRoute.value.params.machineId);
          mItem.group_id = Number(formValue.value.permission_type.split('-')[1]);
          machineses.push(mItem);
        });
      });
      // context.emit('valid');
      try {
        Promise.all(machineses.map(item => axios.server.post('/v1/vmachine', item)))
          .then(axios.server.spread(res => {
            // 请求1的结果
            console.log('Response:', res);

          }))
          .catch(err => {
            // 请求失败处理
            console.error('err', err);
            window.$notification?.error({
              content: err.data.error_msg || unkonwnErrorMsg,
              duration: 5000,
              keepAliveOnHover: true
            });
          });
        context.emit('close');
      } catch (outErr) {
        console.error('outErr', outErr);
      }
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
    permission_type: undefined,
    version_types: []
  };
};
const pmData = ref();
const getProductOptions = () => {
  getProductOpts(productOpts);
};
const clickBasicInfo = ref(null);
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
      formValue.value.version && getMilestoneOpts(milestoneOpts, formValue.value.version);
    }
  );
};

watch(
  () => formValue.value.method,
  () => {
    if (clickBasicInfo.value && clickBasicInfo.value.method) {
      clickBasicInfo.value.method = formValue.value.method;
      if (clickBasicInfo.value.method === 'import') {
        variableCapacity.value.forEach(item => {
          item.capacity = null;
        });
      } else {
        variableCapacity.value.forEach(item => {
          item.capacity = 50;
        });
      }
    }
  }
);

watch(
  () => formValue.value.product,
  () => {
    if (clickBasicInfo.value && clickBasicInfo.value.product) {
      clickBasicInfo.value.product = formValue.value.product;
    }
  }
);

watch(
  () => formValue.value.version,
  () => {
    if (clickBasicInfo.value && clickBasicInfo.value.version) {
      clickBasicInfo.value.version = formValue.value.version;
    }
  }
);

const isIncludeMilestone = ref(false);

watch(
  () => formValue.value.milestone_id,
  () => {
    getIsDisableAddItem();
    if (clickBasicInfo.value && clickBasicInfo.value.milestone_id) {
      clickBasicInfo.value.milestone_id = formValue.value.milestone_id;
    }
  }
);
const getIsDisableAddItem = () => {
  let basics = [];
  formValue.value.version_types.forEach(item => basics.push(item.basicInfo.milestone_id));
  basics = Array.from(new Set(basics));
  if (basics.includes(formValue.value.milestone_id)) {
    isIncludeMilestone.value = true;
  } else {
    isIncludeMilestone.value = false;
  }
};
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

function handleCheck(check, checkItem) {
  checkedPm.value = [check?.pop()];
  [checkItem.pmachine_id] = checkedPm.value;
  checkItem.pmachine_name = pmData.value.find((item) => item.id === checkItem.pmachine_id).ip;
}
const renderIcon = () => {
  return h(NIcon, null, {
    default: () => h(Add)
  });
};
const removeItem = (index) => {
  formValue.value.version_types.splice(index, 1);
  getIsDisableAddItem();
};

const addItem = () => {
  let basicInfo = {
    method: formValue.value.method,
    product: formValue.value.product,
    version: formValue.value.version,
    milestone_id: formValue.value.milestone_id,
    milestone_name: formValue.value.milestone_name,
  };
  formValue.value.version_types.push({
    machines: [{
      frame: 'aarch64',
      machine_num: 1,
      cpu_mode: 'host-passthrough',
      memory: 4096,
      capacity: formValue.value.method === 'import' ? null : 50,
      pm_select_mode: 'auto',
      sockets: 1,
      cores: 1,
      threads: 1
    }, {
      frame: 'x86_64',
      machine_num: 1,
      cpu_mode: 'host-passthrough',
      memory: 4096,
      capacity: formValue.value.method === 'import' ? null : 50,
      pm_select_mode: 'auto',
      sockets: 1,
      cores: 1,
      threads: 1
    }], basicInfo
  });
  getIsDisableAddItem();
};
const handleUpdateMilestone = (value, option) => {
  formValue.value.milestone_name = option.label;
};
const configRef = ref(false);
const boxIndex = ref(null);
const handleClick = (typeIndex, index, tag) => {
  boxIndex.value = `${typeIndex}-${index}`;
  if (tag === 'expand') {
    configRef.value = true;
  } else {
    configRef.value = false;
  }
};
const variableCapacity = ref(null);
const handleClickCard = (item) => {
  clickBasicInfo.value = item.basicInfo;
  formValue.value.method = item.basicInfo.method;
  formValue.value.product = item.basicInfo.product;
  formValue.value.version = item.basicInfo.version;
  formValue.value.milestone_id = item.basicInfo.milestone_id;
  variableCapacity.value = item.machines;
};

const handleClickMachineNum = (value, tag) => {
  value.machines?.forEach(item => {
    if (tag === 'add' && item.machine_num <= 4) {
      item.machine_num = item.machine_num + 1;
    } else if (tag === 'reduce' && item.machine_num >= 2) {
      item.machine_num = item.machine_num - 1;
    }
  });
};
export default {
  checkedPm,
  size,
  pmcolumns,
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
  changeFrameAndNumber,
  renderIcon,
  removeItem,
  addItem,
  handleUpdateMilestone,
  handleClick,
  configRef,
  boxIndex,
  isIncludeMilestone,
  handleUpdatePmSelectMode,
  handleClickCard,
  handleClickMachineNum,
};
