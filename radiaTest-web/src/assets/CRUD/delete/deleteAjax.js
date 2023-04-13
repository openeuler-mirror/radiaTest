import axios from '@/axios';
import { h } from 'vue';

const handleDeleteFail = (id, mesg) => {
  window.$notification?.error({
    content: `ID:${id} 删除失败`,
    meta: () => {
      return h('div', null, [h('p', null, `原因：   ${mesg}`)]);
    }
  });
};

const handleDeleteSuccess = (id) => {
  window.$message?.success(`ID:${id} 删除成功`);
};

const singleDelete = async (url, id, store) => {
  await axios
    .delete(url)
    .then(() => {
      handleDeleteSuccess(id);
      store ? store.commit('selected/setDeletedData', [id]) : 0;
    })
    .catch((err) => {
      handleDeleteFail(id, err.data.error_msg);
    });
};

const batchDelete = (url, idList, store) => {
  for (let i in idList) {
    singleDelete(`${url}/${idList[i]}`, idList[i], store);
  }
};

export default {
  handleDeleteSuccess,
  handleDeleteFail,
  batchDelete,
  singleDelete
};
