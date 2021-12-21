import axios from '@/axios';

const getData = (data, loading, total, props) => {
  loading.value = true;
  axios
    .get('/v1/milestone/issues', {
      enterprise: 'open_euler', // TODO 从storage可以获得么
      state: 'all',
      sort: 'updated',
      direction: 'desc',
      milestone: props.form.name,
    })
    .then((res) => {
      data.value = res.filter((item) => item.issue_type === '缺陷');
      total.value = data.value.length;
      loading.value = false;
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
