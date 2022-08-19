import { h } from 'vue';
import axios from '@/axios';

const handleSuccessUpdate = () => {
  window.$notification?.success({
    content: '修改成功',
    duration: 2000
  });
};
const handleFailUpdate = (msg) => {
  window.$notification?.error({
    content: '存在修改错误',
    meta: () => {
      return h('p', null, `原因： ${msg}`);
    }
  });
};
const putForm = (url, formValue) => {
  return new Promise((resolve, reject) => {
    axios
      .put(`${url}/${formValue.value.id}`, formValue.value)
      .then((res) => {
        if (res.error_code === '2000') {
          handleSuccessUpdate();
        } else {
          handleFailUpdate(res.error_msg);
        }
        resolve();
      })
      .catch((error) => {
        if (Object.prototype.toString.call(error) === '[object Object]') {
          handleFailUpdate(error.data.error_msg);
        } else {
          handleFailUpdate(error);
        }
        reject(error);
      });
  });
};
const putFormEmitClose = (url, formValue, context) => {
  return new Promise((resolve, reject) => {
    axios
      .put(`${url}/${formValue.value.id}`, formValue.value)
      .then((res) => {
        if (res.error_code === '2000') {
          handleSuccessUpdate();
          context.emit('close');
        } else {
          handleFailUpdate(res.error_msg);
        }
        resolve();
      })
      .catch((error) => {
        handleFailUpdate(error);
        reject(error);
      });
  });
};

export default {
  handleFailUpdate,
  handleSuccessUpdate,
  putForm,
  putFormEmitClose
};
