import axios from '@/axios';
import { h } from 'vue';

const handleDeleteFail = (mesg) => {
  window.$notification?.error({
    content: '删除失败',
    meta: () => {
      return h('div', null, [
        h('p', null, `原因：   ${mesg}`),
      ]);
    },
  });
};

const handleDeleteSuccess = () => {
  window.$notification?.success({
    content: ' 删除成功',
    duration: 2000,
  });
};

const postDelete = (url, idList, store, selected) => {
  axios
    .delete(url, { id: idList })
    .then((res) => {
      if (res.error_code === '2000') {
        handleDeleteSuccess();
        store
          ? store.commit('selected/setDeletedData', selected.value)
          : 0;
      } else {
        handleDeleteFail(res.error_msg);
      }
    })
    .catch((err) => {
      if (err.data.validation_error) {
        handleDeleteFail(err.data.validation_error.body_params[0].msg);
      } else {
        handleDeleteFail('发生未知错误，请联系管理员进行处理');
      }
    });
};

export default {
  handleDeleteSuccess,
  handleDeleteFail,
  postDelete,
};
