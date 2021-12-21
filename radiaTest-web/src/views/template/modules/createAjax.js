import { ref } from 'vue';
import { createAjax } from '@/assets/CRUD/create';
import axios from '@/axios';
import { storage } from '@/assets/utils/storageUtils';

const getData = (options, loading) => {
  loading.value = true;
  axios
    .get('/v1/suite')
    .then((res) => {
      options.value = res.map((item) => {
        return {
          key: item.id,
          label: item.name,
          children: []
        };
      });
      axios
        .get('/v1/case')
        .then((resp) => {
          resp.forEach((item) => {
            if (item.suite_id) {
              options.value.filter(suite => suite.key === item.suite_id)[0].children.push({ label: item.name, key: item.name });
            }
          });
          loading.value = false;
        });
    })
    .catch(() => {
      window.$message?.error('无法连接服务器，请检查网络连接');
    });
};

const postForm = (formValue, casesValue) => {
  const postData = ref({
    name: formValue.value.name,
    template_type: formValue.value.template_type,
    owner: formValue.value.owner,
    milestone_id: formValue.value.milestone,
    description: formValue.value.description,
    cases: casesValue.value,
    author: storage.getValue('gitee_name')
  });
  createAjax.postForm('/v1/template', postData);
};

export default {
  getData,
  postForm,
};
