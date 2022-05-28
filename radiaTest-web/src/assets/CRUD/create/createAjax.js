import { h } from 'vue';
import axios from '@/axios';

const handleFailCreate = (mesg) => {
  window.$notification?.error({
    content: '注册失败',
    meta: () => {
      return h('div', null, [
        h('p', null, `原因：   ${mesg}`),
      ]);
    },
  });
};

const handleSuccessCreate = () => {
  window.$notification?.success({
    content: '注册成功',
    duration: 2000
  });
};

const postForm = (url, form) => {
  return new Promise((resolve, reject) => {
    axios
      .post(url, form.value)
      .then((res) => {
        handleSuccessCreate();
        resolve({ result: res,form:form.value});
      })
      .catch((err) => {
        handleFailCreate(res.error_msg);
        reject(err);
      });
  });
};

export default {
  handleFailCreate,
  handleSuccessCreate,
  postForm,
};
