import axios from '@/axios';
import { storage } from '@/assets/utils/storageUtils';
import { createTemplate } from '@/api/post.js';

const createChildren = (arr) => {
  let tempArr = [];
  arr.forEach((item) => {
    tempArr.push({
      label: item.case_name,
      key: `case-${item.case_id}`
    });
  });

  return tempArr;
};

const getData = (options, id) => {
  return axios
    .get(`/v1/template/cases/${id}`)
    .then((res) => {
      options.value = [];
      res.data.forEach((item) => {
        options.value.push({
          label: item.suite_name,
          key: `suite-${item.suite_id}`,
          children: createChildren(item.case)
        });
      });
    })
    .catch(() => {
      window.$message?.error('无法连接服务器，请检查网络连接');
    });
};

const exchangeCases = (cases) => {
  return cases?.map((item) => {
    return item.replace('case-', '');
  });
};

const postForm = (formValue, isUploadCases) => {
  const formData = new FormData();
  formData.append('name', formValue.value.name);
  formData.append('milestone_id', formValue.value.milestone_id);
  formData.append('description', formValue.value.description);
  formData.append('git_repo_id', formValue.value.git_repo_id);
  formData.append('permission_type', formValue.value.permission_type.split('-')[0]);
  formData.append('creator_id', storage.getValue('user_id'));
  formData.append('org_id', storage.getValue('loginOrgId'));
  if (formValue.value.permission_type.includes('group')) {
    formData.append('group_id', Number(formValue.value.permission_type.split('-')[1]));
  }
  if (isUploadCases) {
    formData.append('file', formValue.value.file[0]?.file);
  } else {
    formData.append('cases', exchangeCases(formValue.value.cases).join(','));
  }

  formValue.value.permission_type = formValue.value.permission_type.split('-')[0];
  formValue.value.creator_id = storage.getValue('user_id');
  formValue.value.org_id = storage.getValue('loginOrgId');
  if (formValue.value.permission_type.includes('group')) {
    formValue.value.group_id = Number(formValue.value.permission_type.split('-')[1]);
  }
  formValue.value.cases = exchangeCases(formValue.value.cases).join(',');

  let params = isUploadCases ? formData : formValue.value;
  return createTemplate(params);
};

export default {
  getData,
  postForm,
  exchangeCases
};
