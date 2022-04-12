import axios from '@/axios';
import { h, ref } from 'vue';
import { NAvatar, NDropdown, NTag, NText } from 'naive-ui';
import { selectdRole } from './roleMenu';
const loading = ref(false);
const usersData = ref([]);
const roleList = ref([]);
let requestUrl;

const pagination = ref({
  page: 1,
  pageCount: 1,
  pageSize: 10,
});
const actionUrl = ref('');

function getUserTableData() {
  loading.value = true;
  axios
    .get(actionUrl.value, {
      page_num: pagination.value.page,
      page_size: pagination.value.pageSize,
    })
    .then((res) => {
      loading.value = false;
      pagination.value.pageCount = res.data.pages;
      usersData.value = res.data?.items?.map((item) => item);
    })
    .catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
      loading.value = false;
    });
}
function getRoleList() {
  axios.get('/v1/role').then((res) => {
    roleList.value = [];
    if (selectdRole.value === 'public') {
      res.data.forEach((item) => {
        if (item.type === 'public') {
          roleList.value.push({
            label: item.name,
            value: String(item.id),
          });
        }
      });
    } else {
      const [key,id] = window.atob(selectdRole.value).split('-');
      res.data.forEach((item) => {
        if (item.type === key && item[`${key}_id`] === Number(id)) {
          roleList.value.push({
            label: item.name,
            value: String(item.id),
          });
        }
      });
    }
  });
}
function getUserInfo() {
  if (selectdRole.value === 'public') {
    requestUrl = '/v1/user_role';
    actionUrl.value = '/v1/users';
    getUserTableData();
    getRoleList();
  } else {
    const [key, id] = window.atob(selectdRole.value).split('-');
    if (key) {
      requestUrl = `/v1/user_role/${key}/${id}`;
      actionUrl.value = `/v1/${key === 'group' ? 'groups' : 'org'}/${id}/users`;
      getUserTableData();
      getRoleList();
    }
  }
}
function handlePageChange(page) {
  pagination.value.page = page;
  getUserTableData();
}
function deleteRole(row) {
  axios
    .delete(requestUrl, {
      user_id: row.gitee_id,
      role_id: row.role.id,
    })
    .then(() => {
      getUserInfo();
    })
    .catch((err) => window.$message?.error(err.data.error_msg || '未知错误'));
}

function selectRole(row, option) {
  axios
    .post(requestUrl, {
      user_id: row.gitee_id,
      role_id: Number(option.value),
    })
    .then(() => {
      getUserInfo();
    })
    .catch((err) => window.$message?.error(err.data.error_msg || '未知错误'));
}
const usersColumns = [
  {
    title: '',
    key: 'avatar_url',
    align: 'center',
    render(row) {
      return h(NAvatar, { size: 'small', src: row.avatar_url });
    },
  },
  {
    title: '用户',
    key: 'gitee_name',
    align: 'center',
    render(row) {
      return h('span', null, [row.gitee_name]);
    },
  },
  {
    title: '手机号',
    key: 'phone',
    align: 'center',
  },
  {
    title: '角色',
    key: 'role',
    align: 'center',
    render (row) {
      const tag = h(
        NTag,
        {
          type: 'info',
          closable: true,
          onClose: () => deleteRole(row),
        },
        row.role?.name
      );
      const dropList = h(
        NDropdown,
        {
          trigger: 'click',
          options: roleList.value,
          onSelect: (index, item) => selectRole(row, item),
        },
        h(
          NText,
          {
            type: 'info',
            style: 'cursor:pointer',
          },
          '添加角色'
        )
      );
      return row.role ? tag : dropList;
    },
  },
];
export {
  loading,
  roleList,
  usersData,
  usersColumns,
  pagination,
  getUserInfo,
  handlePageChange,
};
