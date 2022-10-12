import { ref } from 'vue';
// import axios from '@/axios';
// import { NSelect } from 'naive-ui';
import { implementTemplate } from '@/api/post';
import { getTemplateInfo, getPm, getVm, getMachineGroup } from '@/api/get';
import { unkonwnErrorMsg } from '@/assets/utils/description';

const machineGroups = ref([]);
function getMachineGroupOptions() {
  getMachineGroup().then((res) => {
    machineGroups.value = res.data.map((item) => ({ label: item.name, value: String(item.id) }));
  });
}
const execModalRef = ref();
const defaultProp = {
  select_mode: 'auto',
  strict_mode: false,
  vmachine_list: [],
  pmachine_list: []
};
const formValue = ref({ ...defaultProp, machine_group_id: undefined });

const postExecData = () => {
  if (formValue.value.strict_mode) {
    if (
      formValue.value.vmachine_list.length !== formValue.value.vm_req_num ||
      formValue.value.pmachine_list.length !== formValue.value.pm_req_num
    ) {
      window.$message?.error('严格模式下,需要选择相应数量的机器');
      return;
    }
  }

  implementTemplate({
    template_id: formValue.value.id,
    template_name: formValue.value.name,
    frame: formValue.value.frame,
    pmachine_list: formValue.value.pmachine_list,
    vmachine_list: formValue.value.vmachine_list,
    machine_policy: formValue.value.select_mode,
    strict_mode: formValue.value.strict_mode,
    machine_group_id: formValue.value.machine_group_id,
    creator_id: formValue.value.git_repo.creator_id,
    org_id: formValue.value.git_repo.org_id,
    taskmilestone_id: formValue.value.milestone_id,
    permission_type: formValue.value.git_repo.permission_type,
    group_id: formValue.value.git_repo.group_id
  })
    .then((res) => {
      if (res.error_code === '2000') {
        window.$notification?.success({
          content: '测试任务已成功执行',
          meta: `模板：${formValue.value.name}`,
          duration: 2000
        });
        formValue.value.frame = null;
        execModalRef.value.close();
      }
    })
    .catch((err) => {
      if (!err.message && !err.data.validation_error) {
        window.$message?.error('发生未知错误，执行失败，请联系管理员进行处理');
      } else if (err.data.validation_error) {
        window.$message?.error(err.data.validation_error.body_params[0].msg);
      } else {
        window.$message?.error(err.message);
      }
      formValue.value.frame = null;
    });
};

const pmOpt = ref();
const vmOpt = ref();

const renderExecute = (row) => {
  getTemplateInfo(row.id).then((res) => {
    formValue.value = { ...res.data, ...row, ...defaultProp };
  });
  getMachineGroupOptions();
};

const handleExecClick = async (row) => {
  renderExecute(row);
  execModalRef.value.show();
};
const checkedVm = ref([]);
const checkedPm = ref([]);
function selectmachine(type, value) {
  if (type === 'pm') {
    if (formValue.value.strict_mode && formValue.value.pm_req_num < value.length) {
      window.$message?.error('严格模式下,需要选择相应数量的机器');
      return;
    }
    checkedPm.value = value;
    formValue.value.pmachine_list = value;
  } else {
    if (formValue.value.strict_mode && formValue.value.vm_req_num < value.length) {
      window.$message?.error('严格模式下,需要选择相应数量的机器');
      return;
    }
    checkedVm.value = value;
    formValue.value.vmachine_list = value;
  }
}
async function changeFrame() {
  try {
    if (formValue.value.frame && formValue.value.machine_group_id) {
      const data = await getPm({
        frame: formValue.value.frame,
        machine_purpose: 'run_job',
        machine_group_id: formValue.value.machine_group_id
      });
      pmOpt.value = data.data;
      checkedVm.value = [];
      checkedPm.value = [];
      formValue.value.pmachine_list = [];
      formValue.value.vmachine_list = [];
      const vmdata = await getVm({
        frame: formValue.value.frame,
        machine_purpose: 'run_job',
        machine_group_id: formValue.value.machine_group_id
      });
      vmOpt.value = vmdata.data;
    }
  } catch (error) {
    window.$message?.error(error.data?.error_msg || error.message || unkonwnErrorMsg);
  }
}
function renderText(type, values) {
  const result = [];
  if (values.length) {
    values.forEach((item) => {
      const element = type === 'vm' ? vmOpt.value.find((i) => i.id === item) : pmOpt.value.find((i) => i.id === item);
      result.push(element?.ip);
    });
    return result.join(',');
  }
  return '';
}
const rules = {
  machine_group_id: {
    required: true,
    message: '请选择机器组',
    trigger: ['blur']
  },
  frame: {
    required: true,
    message: '请选择架构',
    trigger: ['blur']
  }
};

export {
  rules,
  handleExecClick,
  formValue,
  execModalRef,
  postExecData,
  pmOpt,
  vmOpt,
  selectmachine,
  checkedPm,
  checkedVm,
  changeFrame,
  renderText,
  machineGroups
};
