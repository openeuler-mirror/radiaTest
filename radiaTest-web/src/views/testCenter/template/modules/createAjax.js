import { ref } from 'vue';
import { createAjax } from '@/assets/CRUD/create';
import axios from '@/axios';
import { storage } from '@/assets/utils/storageUtils';

const createChildren = (arr) => {
  let tempArr = [];
  arr.forEach((item) => {
    tempArr.push({
      label: item.case_name,
      key: item.case_id
    });
  });

  return tempArr;
};

const getData = (options, id) => {
  axios
    .get(`/v1/template/cases/${id}`)
    .then((res) => {
      options.value = [];
      res.data.forEach((item) => {
        options.value.push({
          label: item.suite_name,
          key: item.suite_id,
          children: createChildren(item.case)
        });
      });
    })
    .catch(() => {
      window.$message?.error('无法连接服务器，请检查网络连接');
    });
};

const postForm = (formValue) => {
  const postData = ref({
    name: formValue.value.name,
    milestone_id: formValue.value.milestone_id,
    description: formValue.value.description,
    git_repo_id: formValue.value.git_repo_id,
    cases: formValue.value.cases,
    permission_type: formValue.value.permission_type.split('-')[0],
    creator_id: Number(storage.getValue('gitee_id')),
    org_id: storage.getValue('orgId'),
    group_id: Number(formValue.value.permission_type.split('-')[1])
  });
  createAjax.postForm('/v1/template', postData);
};

export default {
  getData,
  postForm
};
