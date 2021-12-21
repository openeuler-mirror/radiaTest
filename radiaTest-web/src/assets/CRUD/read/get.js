import axios from '@/axios';
import { any2standard } from '@/assets/utils/dateFormatUtils';

const list = (url, data, loading) => {
  loading
    ? loading.value = true
    : 0;
  axios
    .get(url)
    .then((res) => {
      if (!res.error_mesg) {
        res.map((item) => {
          item.start_time
            ? item.start_time = any2standard(item.start_time)
            : 0;
          item.end_time
            ? item.end_time = any2standard(item.end_time)
            : 0;
          item.create_time
            ? item.start_time = any2standard(item.start_time)
            : 0;
          item.update_time
            ? item.end_time = any2standard(item.end_time)
            : 0;
        });
        data.value = res;
      } else {
        window.$message?.error(`获取数据失败：${res.error_mesg}`);
      }
      loading
        ? loading.value = false
        : 0;
    })
    .catch(() => {
      window.$message?.error('发生未知错误，获取数据失败');
      loading
        ? loading.value = false
        : 0;
    });
};

const refresh = (url, data, loading) => {
  if (!loading.value) {
    list(url, data, loading);
  }
};

const filter = (url, data, loading, filters) => {
  loading.value = true;
  axios
    .get(url, filters)
    .then((res) => {
      if (!res.error_mesg) {
        res.map((item) => {
          item.start_time
            ? item.start_time = any2standard(item.start_time)
            : 0;
          item.end_time
            ? item.end_time = any2standard(item.end_time)
            : 0;
          item.create_time
            ? item.start_time = any2standard(item.start_time)
            : 0;
          item.update_time
            ? item.end_time = any2standard(item.end_time)
            : 0;
        });
        data.value = res;
      } else {
        window.$message?.error(`获取数据失败：${res.error_mesg}`);
      }
      loading.value = false;
    })
    .catch(() => {
      window.$message?.error('发生未知错误，获取数据失败');
      loading.value = false;
    });
};

export default {
  list,
  refresh,
  filter,
};
