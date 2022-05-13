import axios from '@/axios';
import router from '@/router';
import { ref, h } from 'vue';
import { NAvatar } from 'naive-ui';
import { setRuleData, setRoleInfo } from './rulestable';
import { getRoleList } from '@/views/personalCenter/authorityManagement/modules/role';
import { unkonwnErrorMsg } from '@/assets/utils/description';
const roleId = ref();
const titles = ref([]);
const data = ref([]);
const description = ref('');
const columns = [
  {
    title: '',
    key: 'avatar_url',
    align: 'center',
    render (row) {
      return h(NAvatar, { size: 'small', src: row.avatar_url });
    },
  },
  {
    title: '用户',
    key: 'gitee_name',
    align: 'center',
    render (row) {
      return h('span', null, [row.gitee_name]);
    },
  },
  {
    title: '手机号',
    key: 'phone',
    align: 'center',
  },
  {
    title: '邮箱',
    key: 'cla_email',
    align: 'center',
  },
];
const pagination = {
  pageSize: 5,
};
function renderTitles (option) {
  titles.value = [];
  if (option.type === 'public') {
    titles.value.push('公共角色', option.name);
  } else if (option.type === 'person') {
    titles.value.push('个人角色', option.group_name, option.name);
  } else if (option.type === 'group') {
    titles.value.push('团队角色', option.group_name, option.name);
  } else if (option.type === 'org') {
    titles.value.push('组织角色', option.org_name, option.name);
  }
}
function getRoleInfo (options = {}) {
  roleId.value = window
    .atob(router.currentRoute.value.params.roleId)
    .split('-')
    .pop();
  axios.get(`/v1/role/${roleId.value}`, options).then((res) => {
    renderTitles(res.data);
    description.value = res.data.description;
    data.value = res.data.users;
    setRoleInfo(res.data);
    setRuleData(res.data.scopes);
  }).catch(err => {
    window.$message?.error(err.data?.error_msg || err.message || unkonwnErrorMsg);
  });
}
function deleteRole () {
  axios.delete(`/v1/role/${roleId.value}`).then(() => {
    router.push({ name: 'authorityManagement' }).then(() => {
      getRoleList();
    });
  }).catch(err => {
    window.$message?.error(err.data?.error_msg || err.message || unkonwnErrorMsg);
  });
}
export {
  description,
  titles,
  pagination,
  columns,
  data,
  roleId,
  getRoleInfo,
  deleteRole,
};
