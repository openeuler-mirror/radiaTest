import { ref } from 'vue';
import { createAjax } from '@/assets/CRUD/create';
import axios from '@/axios';
import { storage } from '@/assets/utils/storageUtils';

const getData = (options, id) => {
  axios
    .get(`/v1/template/cases/${id}`)
    .then((res) => {
      const suites = new Map();
      res.data.forEach((item) => {
        if (!suites.has(item.suite_id)) {
          suites.set(item.suite_id, {
            key: item.suite_id,
            label: item.suite,
            children: [
              {
                key: item.id,
                label: item.name,
              },
            ],
          });
        } else {
          suites.get(item.suite_id).children.push({
            key: item.id,
            label: item.name,
          });
        }
      });
      for (let suite of suites.values()) {
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
    milestone_id: formValue.value.milestone,
    description: formValue.value.description,
    git_repo_id: formValue.value.git_repo,
    cases: casesValue.value,
    permission_type: formValue.value.permission_type.split('-')[0],
    creator_id: Number(storage.getValue('gitee_id')),
    org_id: storage.getValue('orgId'),
    group_id: Number(formValue.value.permission_type.split('-')[1]),
  });
  console.log(postData.value, formValue.value);
  createAjax.postForm('/v1/template', postData);
};

export default {
  getData,
  postForm,
};
