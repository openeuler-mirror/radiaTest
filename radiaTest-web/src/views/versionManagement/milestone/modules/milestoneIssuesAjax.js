import { getIssue } from '@/api/get';

const getData = (data, loading, total, props, page) => {
  console.log(props);
  loading.value = true;
  getIssue({
    page: page.page,
    per_page: page.pageSize,
    milestone_id: props.form.id,
  })
    .then((res) => {
      const resData = JSON.parse(res.data);
      data.value = resData.data;
      total.value = resData.total_count;
      loading.value = false;
      page.pageCount = Math.ceil(Number(total.value) / page.pageSize) || 1;
    })
    .catch((err) => {
      if (err.data.validation_error) {
        window.$message.error(err.data.validation_error.body_params[0].msg);
      } else {
        window.$message.error('发生未知错误，获取数据失败');
      }
      loading.value = false;
    });
};

export default {
  getData,
};
