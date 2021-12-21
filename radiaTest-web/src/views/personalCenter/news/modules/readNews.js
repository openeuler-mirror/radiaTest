import { ref, reactive } from 'vue';

import { changeLoadingStatus } from '@/assets/utils/loading';
import axios from '@/axios';

const readPageInfo = reactive({
  page: 1,
  pageCount: 1,
  pageSize: 7,
});
const readNewsList = ref([]);
function getReadNews () {
  changeLoadingStatus(true);
  axios.get('/v1/msg', { has_read: 1, page_num: readPageInfo.page, page_size: readPageInfo.pageSize }).then(res => {
    readNewsList.value = res.data.items ? res.data.items : [];
    readPageInfo.pageCount = res.data.pages;
    changeLoadingStatus(false);
  }).catch((error) => {
    window.$message?.error(error.data.error_msg||'未知错误');
    changeLoadingStatus(false);
  });
}
function readPageChange (index) {
  readPageInfo.page = index;
  getReadNews();
}


export {
  readNewsList,
  readPageInfo,
  getReadNews,
  readPageChange,
};
