import { ref } from 'vue';
// import axios from '@/axios';
// import { NSelect } from 'naive-ui';
import { implementTemplate } from '@/api/post';
import { getTemplateInfo } from '@/api/get';
import { createPmOptions, createVmOptions } from '@/assets/utils/getOpts';

const formValue = ref();
const execModalRef = ref();
const defaultProp = {
  select_mode: 'auto',
  strict_mode: false,
  vmachine_list: [],
  pmachine_list: [],
};
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
  })
    .then((res) => {
      if (res.error_code === '2000') {
        window.$notification?.success({
          content: '测试任务已执行完成',
          meta: `模板：${formValue.value.name}`,
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
    console.log(formValue.value);
  });
};

const handleExecClick = async (row) => {
  renderExecute(row);
  if (!pmOpt.value) {
    pmOpt.value = await createPmOptions();
  }
  if (!vmOpt.value) {
    vmOpt.value = await createVmOptions();
  }
  execModalRef.value.show();
};
function selectmachine(type, value) {
  if (type === 'pm') {
    if (
      formValue.value.strict_mode &&
      formValue.value.pm_req_num < value.length
    ) {
      window.$message?.error('严格模式下,需要选择相应数量的机器');
      return;
    }
    formValue.value.pmachine_list = value;
  } else {
    if (
      formValue.value.strict_mode &&
      formValue.value.vm_req_num < value.length
    ) {
      window.$message?.error('严格模式下,需要选择相应数量的机器');
      return;
    }
    formValue.value.vmachine_list = value;
  }
}

export {
  handleExecClick,
  formValue,
  execModalRef,
  postExecData,
  pmOpt,
  vmOpt,
  selectmachine,
};
