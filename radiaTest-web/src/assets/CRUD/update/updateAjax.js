import { h } from 'vue';
import axios from '@/axios';

const handleSuccessUpdate = () => {
  window.$notification?.success({
    content: '修改成功',
  });
};
const handleFailUpdate = (msg) => {
  window.$notification?.error({
    content: '存在修改错误',
    meta: () => {
      return h('p', null, `原因： ${msg}`);
    },
  });
};
const putForm = (url, formValue) => {
  axios
    .put(url, formValue.value)
    .then((res) => {
      if (res.error_code === '2000') {
        handleSuccessUpdate();
      } else {
        handleFailUpdate(res.error_msg);
      }
    })
    .catch((error) => {
      handleFailUpdate(error);
    });
};
const putFormEmitClose = (url, formValue, context) => {
  axios
    .put(url, formValue.value)
    .then((res) => {
      if (res.error_code === '2000') {
        handleSuccessUpdate();
        context.emit('close');
      } else {
        handleFailUpdate(res.error_msg);
      }
    })
    .catch((error) => {
      handleFailUpdate(error);
    });
};

export default {
  handleFailUpdate,
  handleSuccessUpdate,
  putForm,
  putFormEmitClose,
};
