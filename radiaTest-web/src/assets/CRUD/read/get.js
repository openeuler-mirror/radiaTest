import axios from '@/axios';
import { any2standard } from '@/assets/utils/dateFormatUtils';
import { unkonwnErrorMsg } from '@/assets/utils/description.js';

const list = (url, data, loading, params, page) => {
  loading ? (loading.value = true) : 0;
  axios
    .get(url, params)
    .then((res) => {
      let resData;
      if (Array.isArray(res.data)) {
        resData = res.data;
      } else {
        resData = res.data.items;
      }
      resData.forEach((item) => {
        item.start_time ? (item.start_time = any2standard(item.start_time)) : 0;
        item.end_time ? (item.end_time = any2standard(item.end_time)) : 0;
        item.create_time
          ? (item.start_time = any2standard(item.start_time))
          : 0;
        item.update_time ? (item.end_time = any2standard(item.end_time)) : 0;
      });
      data.value = resData;
      loading ? (loading.value = false) : 0;
      page?.value && (page.value.pageCount = res.data.pages || 1);
    })
    .catch((err) => {
      window.$message?.error(err.data?.error_msg || unkonwnErrorMsg);
      loading ? (loading.value = false) : 0;
    });
};

const refresh = (url, data, loading, pramas) => {
  if (!loading.value) {
    list(url, data, loading, pramas);
  }
};

const filter = (url, data, loading, filters) => {
  loading.value = true;
  axios
    .get(url, filters)
    .then((res) => {
      res.data.map((item) => {
        item.start_time ? (item.start_time = any2standard(item.start_time)) : 0;
        item.end_time ? (item.end_time = any2standard(item.end_time)) : 0;
        item.create_time
          ? (item.start_time = any2standard(item.start_time))
          : 0;
        item.update_time ? (item.end_time = any2standard(item.end_time)) : 0;
      });
      data.value = res.data;
      loading.value = false;
    })
    .catch((err) => {
      window.$message?.error(err.data?.error_msg || unkonwnErrorMsg);
      loading.value = false;
    });
};

export default {
  list,
  refresh,
  filter,
};
