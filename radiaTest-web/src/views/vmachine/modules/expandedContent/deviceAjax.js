import axios from '@/axios';
  
const deleteDevice = (url, target, deviceId) => {
  axios
    .delete(url, { id: deviceId })
    .then((res) => {
      if (res.error_code === 200) {
        window.$message?.success(`${target}已卸载`);
      } else {
        window.$message?.error(`${target}未能卸载：${res.error_mesg}`);
      }
    })
    .catch((err) => {
      if (err.data.validation_error) {
        window.$message?.error(err.data.validation_error.body_params[0].msg);
      } else {
        window.$message?.error(`发生未知错误，${target}卸载失败`);
      }
    });
};

export {
  deleteDevice,
};
