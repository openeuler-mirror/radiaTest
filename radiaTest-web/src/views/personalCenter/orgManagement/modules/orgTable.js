import { ref } from 'vue';

import axios from '@/axios';

const orgs = ref([]);
function getData () {
  axios.get('/v1/admin/org').then(res => {
    orgs.value = res.data;
  });
}

const orgColumns = [
  {
    title: '组织名称',
    key: 'organization_name',
    align: 'center',
  },
  {
    title: 'cla签署地址',
    key: 'cla_sign_url',
    align: 'center',
  },
  {
    title: '验证地址',
    key: 'cla_verify_url',
    align: 'center',
  },
  {
    title: '验证地址的请求方式',
    key: 'cla_request_type',
    align: 'center',
  },
  {
    title: '验证通过的标志',
    key: 'cla_pass_flag',
    align: 'center',
  },
  {
    title: 'cla验证参数',
    key: 'cla_verify_params',
    align: 'center',
    render (row) {
      return JSON.stringify(row.cla_verify_params);
    },
  },
  {
    title: 'body中的参数',
    key: 'cla_verify_body',
    align: 'center',
    render (row) {
      return JSON.stringify(row.cla_verify_body);
    },
  }
];
const pagination = {
  pagesize: 7,
};

export {
  orgs,
  pagination,
  orgColumns,
  getData,
};
