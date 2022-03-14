import axios from '@/axios';

const poweroff = (machineId, disabled) => {
  axios
    .put('/v1/pmachine/power', {
      id: machineId,
      status: 'off',
    })
    .then((res) => {
      if (res.error_code === '2000') {
        window.$message?.success('已成功下电');
      } else {
        window.$message?.error(`下电失败：${res.error_msg}`);
      }
      disabled.value = false;
    })
    .catch((err) => {
      if (err.data.validation_error) {
        window.$message?.error(err.data.validation_error.body_params[0].msg);
      } else {
        window.$message?.error('发生未知错误，下电失败');
      }
      disabled.value = false;
    });
};

const poweron = (machineId, disabled) => {
  axios
    .put('/v1/pmachine/power', {
      id: machineId,
      status: 'on',
    })
    .then((res) => {
      if (res.error_code === '2000') {
        window.$message?.success('已成功上电');
      } else {
        window.$message?.error(`上电失败：${res.error_msg}`);
      }
      disabled.value = false;
    })
    .catch((err) => {
      if (err.data.validation_error) {
        window.$message?.error(err.data.validation_error.body_params[0].msg);
      } else {
        window.$message?.error('发生未知错误，上电失败');
      }
      disabled.value = false;
    });
};

const handlePowerClick = (machineId, status, disabled) => {
  disabled.value = true;
  if (status === 'on') {
    poweroff(machineId, disabled);
  } else if (status === 'off') {
    poweron(machineId, disabled);
  } else {
    window.$message?.error('物理机运行状态未知，请联系管理员进行处理');
    disabled.value = false;
  }

};

export {
  handlePowerClick,
};
