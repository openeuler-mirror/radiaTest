import axios from '@/axios';
import { h } from 'vue';

const handleDeleteFail = (id, mesg) => {
  window.$notification?.error({
    content: `ID:${id} 删除失败`,
    meta: () => {
      return h('div', null, [
        h('p', null, `原因：   ${mesg}`),
      ]);
    },
  });
};

const handleDeleteSuccess = (id) => {
  window.$message?.success(`ID:${id} 删除成功`);
};

const singleDelete = (url, id, store) => {
  axios
    .delete(url)
    .then((res) => {
      if (res.error_code === '2000') {
        handleDeleteSuccess();
        store
          ? store.commit('selected/setDeletedData', [id])
          : 0;
      } else {
        handleDeleteFail(id, res.error_msg);
      }
    })
    .catch((err) => {
      if (err.data.validation_error) {
        handleDeleteFail(id, err.data.validation_error.body_params[0].msg);
      } else {
        handleDeleteFail(id, '发生未知错误，请联系管理员进行处理');
      }
    });
};

const batchDelete = (url, idList, store) => {
  for (let id in idList){
    singleDelete(`${url}/${id}`, id, store);
  }
};

export default {
  handleDeleteSuccess,
  handleDeleteFail,
  batchDelete,
  singleDelete,
};
