import { reactive, ref } from 'vue';

import { changeLoadingStatus } from '@/assets/utils/loading';
import axios from '@/axios';
import request from 'axios';
import { readNewsList, getReadNews } from './readNews';
import { storage } from '@/assets/utils/storageUtils';

const unreadPageInfo = reactive({
  page: 1,
  pageCount: 1,
  pageSize: 7,
  total: 1,
});
const unreadNewsList = ref([]);
function getUnreadNews () {
  changeLoadingStatus(true);
  axios
    .get('/v1/msg', {
      has_read: 0,
      page_num: unreadPageInfo.page,
      page_size: unreadPageInfo.pageSize,
    })
    .then((res) => {
      unreadNewsList.value = res.data.items ? res.data.items : [];
      unreadPageInfo.pageCount = res.data.pages;
      unreadPageInfo.total = res.data.total;
      changeLoadingStatus(false);
    })
    .catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
      changeLoadingStatus(false);
    });
}
function unreadPageChange (index) {
  unreadPageInfo.page = index;
  getUnreadNews();
}
function readAll () {
  changeLoadingStatus(true);
  axios
    .put('/v1/msg/batch', { has_read: true, has_all_read: true })
    .then(() => {
      getUnreadNews();
      getReadNews();
      changeLoadingStatus(false);
    })
    .catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
      changeLoadingStatus(false);
    });
}
function read (index) {
  changeLoadingStatus(true);
  axios
    .put('/v1/msg/batch', {
      msg_ids: [unreadNewsList.value[index].id],
      has_read: true,
    })
    .then(() => {
      getUnreadNews();
      getReadNews();
      changeLoadingStatus(false);
    })
    .catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
      changeLoadingStatus(false);
    });
}
function handleMsg (index, type, action) {
  changeLoadingStatus(true);
  axios
    .put(
      `/v1/users/groups/${type
        ? readNewsList.value[index].data.group_id
        : unreadNewsList.value[index].data.group_id
      }`,
      {
        msg_id: type
          ? readNewsList.value[index].id
          : unreadNewsList.value[index].id,
        access: action,
      }
    )
    .then(() => {
      getUnreadNews();
      getReadNews();
      changeLoadingStatus(false);
    })
    .catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
      changeLoadingStatus(false);
    });
}
function accept (index, type) {
  const item = type ? readNewsList.value[index] : unreadNewsList.value[index];
  if (item.data.group_id) {
    handleMsg(index, type, true);
  } else {
    changeLoadingStatus(true);
    request({
      url: item.data.script,
      method: item.data.method,
      headers: {
        Authorization: `JWT ${storage.getValue('token')}`,
      },
      data: item.data.body,
    })
      .then((res) => {
        if (res.data.error_code !== '2000') {
          return Promise.reject(res);
        }
        axios.put('/v1/msgcallback', {
          msg_id: item.id,
          access: true
        }).then(() => {
          getUnreadNews();
          getReadNews();
        });
        changeLoadingStatus(false);
        return Promise.resolve();
      })
      .catch((err) => {
        window.$message?.error(err.data?.error_msg || err.message || '未知错误');
        changeLoadingStatus(false);
      });
  }
}
function refuse (index, type) {
  const item = type ? readNewsList.value[index] : unreadNewsList.value[index];
  if (item.data.group_id) {
    handleMsg(index, type, false);
  } else {
    axios.put('/v1/msgcallback', {
      msg_id: item.id,
      access: false
    }).then(() => {
      getUnreadNews();
      getReadNews();
    });
  }
}

export {
  unreadPageInfo,
  unreadNewsList,
  getUnreadNews,
  unreadPageChange,
  read,
  refuse,
  accept,
  readAll,
};
