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
  });
};

const postForm = (url, form) => {
  axios
    .post(url, form.value)
    .then((res) => {
      if (res.error_code !== 200) {
        handleFailCreate(res.error_mesg);
      } else {
        handleSuccessCreate();
      }
    })
    .catch((err) => {
      let mesg = '发生未知错误，请联系管理员进行处理';
      if (err.data.validation_error) {
        mesg = err.data.validation_error.body_params[0].msg;
      }
      handleFailCreate(mesg);
      return false;
    });
};

export default {
  handleFailCreate,
  handleSuccessCreate,
  postForm,
};
