import { ref } from 'vue';
import axios from '@/axios';

const disabledAll = ref(false);
const restartValue = ref('reboot');
const shutdownValue = ref('shutdown');

const restartOpts = ref([
  {
    label: 'reboot',
    value: 'reboot',
  },
  {
    label: 'reset',
    value: 'reset',
  },
]);
const shutdownOpts = ref([
  {
    label: 'shutdown',
    value: 'shutdown',
  },
  {
    label: 'destroy',
    value: 'destroy',
  },
]);

const changeState = (machineId, nextStatus) => {
  disabledAll.value = true;
  axios
    .put('/v1/vmachine/power', {
      id: machineId,
      status: nextStatus,
    })
    .then((res) => {
      if (res.error_code === '2000') {
        window.$message?.success(`${nextStatus}succeed`);
        disabledAll.value = false;
      } else {
        window.$message?.error(`${nextStatus}fail, ${res.error_msg}`);
        disabledAll.value = false;
      }
    })
    .catch((err) => {
      let mesg;
      if (err.data.validation_error) {
        mesg = err.data.validation_error.body_params[0].msg;
      } else {
        mesg = '发生未知错误，请联系管理员处理';
      }
      window.$message?.error(mesg);
      disabledAll.value = false;
    });
};

export default {
  disabledAll,
  restartValue,
  shutdownValue,
  restartOpts,
  shutdownOpts,
  changeState,
};

