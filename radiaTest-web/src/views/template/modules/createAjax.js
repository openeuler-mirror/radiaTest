import { ref } from 'vue';
import { createAjax } from '@/assets/CRUD/create';
import axios from '@/axios';
import { storage } from '@/assets/utils/storageUtils';

const getData = (options) => {
  axios
    .get('/v1/case', {usabled: 1})
    .then((res) => {
      const suites = new Map();
      res.forEach((item) => {
        if (!suites.has(item.suite_id)) {
          suites.set(
            item.suite_id,
            {
              key: item.suite_id,
              label: item.suite,
              children: [
                {
                  key: item.id,
                  label: item.name,
                }
              ]
            }
          );
        } else {
          suites.get(item.suite_id).children.push({
            key: item.id,
            label: item.name,
          });
        }
      });
      for ( let suite of suites.values() ) {
        options.value.push(suite);
      }
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
