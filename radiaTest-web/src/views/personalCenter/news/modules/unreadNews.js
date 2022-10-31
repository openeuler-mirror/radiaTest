import { reactive, ref } from 'vue';

import { changeLoadingStatus } from '@/assets/utils/loading';
import axios from '@/axios';
import request from 'axios';
import { getReadNews } from './readNews';
import { storage } from '@/assets/utils/storageUtils';

const unreadPageInfo = reactive({
  page: 1,
  pageCount: 1,
  pageSize: 7,
  total: 0
});
const unreadNewsList = ref([]);
function getUnreadNews() {
  changeLoadingStatus(true);
  axios
    .get('/v1/msg', {
      has_read: 0,
      page_num: unreadPageInfo.page,
      page_size: unreadPageInfo.pageSize
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
function unreadPageChange(page) {
  unreadPageInfo.page = page;
  getUnreadNews();
}
function readAll() {
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
function read(index) {
  changeLoadingStatus(true);
  axios
    .put('/v1/msg/batch', {
      msg_ids: [unreadNewsList.value[index].id],
      has_read: true
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

function handleMsg(item, action) {
  changeLoadingStatus(true);
  let callbackUrl = item.data.callback_url ? item.data.callback_url.slice(4) : `/v1/users/groups/${item.data.group_id}`;

  axios
    .put(callbackUrl, {
      msg_id: item.id,
      access: action
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
function accept(item) {
  if (item.data.group_id) {
    handleMsg(item, true);
  } else {
    changeLoadingStatus(true);
    request({
      url: item.data.script,
      method: item.data.method,
      headers: {
        Authorization: `JWT ${storage.getValue('token')}`
      },
      data: item.data.body
    })
      .then((res) => {
        if (res.data.error_code !== '2000') {
          return Promise.reject(res);
        }
        axios
          .put('/v1/msg/callback', {
            msg_id: item.id,
            access: true
          })
          .then(() => {
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
function refuse(item) {
  if (item.data.group_id) {
    handleMsg(item, false);
  } else {
    axios
      .put('/v1/msg/callback', {
        msg_id: item.id,
        access: false
      })
      .then(() => {
        getUnreadNews();
        getReadNews();
      });
  }
}

export { unreadPageInfo, unreadNewsList, getUnreadNews, unreadPageChange, read, refuse, accept, readAll };
