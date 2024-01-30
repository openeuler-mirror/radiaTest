import { reactive, h, ref } from 'vue';
import { NAvatar, NButton, NSpace, NTag, NDropdown, NText } from 'naive-ui';

import { changeLoadingStatus } from '@/assets/utils/loading';
import { state } from './groupTable';
import { storage } from '@/assets/utils/storageUtils';
import axios from '@/axios';
import { getAllRole, getGroupUser } from '@/api/get';
import { setGroupUserRole } from '@/api/post';
import { deleteGroupUserRole } from '@/api/delete';

const tableLoading = ref(false);
//drawer base information
const groupInfo = reactive({
  name: '',
  usersData: [],
  id: '',
  show: false,
  re_user_group_role_type: '',
});
const groupPagination = reactive({
  pageSize: 10,
  page: 1,
  pageCount: 1,
  itemCount: 1,
  showSizePicker: true,
  pageSizes: [5, 10, 20, 50],
});

// get table data
function getGroupUsers() {
  tableLoading.value = true;
  getGroupUser(groupInfo.id, {
    page_num: groupPagination.page,
    page_size: groupPagination.pageSize
  }).then(res => {
    tableLoading.value = false;
    groupInfo.usersData = res.data.items;
    groupInfo.show = true;
    groupPagination.pageCount = res.data.pages;
    groupPagination.itemCount = res.data.total;
  }).catch((err) => {
    window.$message?.error(err.data.error_msg || '未知错误');
    tableLoading.value = false;
  });
}
const allRole = ref({});
function getGroupRole() {
  getAllRole().then(res => {
    res.data.forEach(item => {
      if (item.type === 'group') {
        allRole.value[item.group_id] ?
          allRole.value[item.group_id].push({ label: item.name, value: String(item.id) }) :
          allRole.value[item.group_id] = [{ label: item.name, value: String(item.id) }];
      }
    });
  });
}

function editGroupUsers(rowIndex) {
  groupInfo.name = state.dataList[rowIndex].groupName;
  groupInfo.id = state.dataList[rowIndex].id;
  groupInfo.re_user_group_id = state.dataList[rowIndex].re_user_group_id;
  groupInfo.re_user_group_role_type = state.dataList[rowIndex].re_user_group_role_type;
  getGroupUsers();
}
function drawerUpdateShow(show) {
  groupInfo.show = show;
}
function groupUserDel(rowIndex) {
  const d = window.$dialog?.warning({
    title: '提示',
    content: '是否要删除该用户?',
    showIcon: false,
    action: () => {
      return h(NSpace,
        {
          style: 'width:100%',
        },
        [
          h(NButton, {
            type: 'error',
            size: 'large',
            ghost: true,
            onClick: () => {
              d.destroy();
            }
          }, ['取消']),
          h(NButton, {
            type: 'primary',
            ghost: true,
            size: 'large',
            onClick: () => {
              changeLoadingStatus(true);
              axios.put(`/v1/groups/${groupInfo.id}/users`, {
                role_type: groupInfo.re_user_group_role_type,
                user_ids: [groupInfo.usersData[rowIndex].user_id],
                is_delete: true,
              }).then(res => {
                groupInfo.usersData.splice(rowIndex, 1);
                changeLoadingStatus(false);
                d.destroy();
                if (res.error_code === '2000') {
                  window.$message?.success('已成功移除该用户!');
                }
              }).catch((err) => {
                window.$message?.error(err.data.error_msg || '未知错误');
                changeLoadingStatus(false);
                d.destroy();
              });
            }
          }, ['确定'])
        ]
      );
    }
  });
}

function selectRole(row, item) {
  setGroupUserRole(groupInfo.id, {
    role_id: Number(item.value),
    user_id: row.user_id
  }).then(() => {
    getGroupUsers();
  });
}
function deleteRole(row) {
  deleteGroupUserRole(groupInfo.id, { user_id: row.user_id, role_id: row.role.id }).then(() => getGroupUsers());
}
//drawer-table columns
const usersColumns = [
  {
    title: '',
    key: 'avatar_url',
    align: 'center',
    render(row) {
      return h(NAvatar, { size: 'small', src: row.avatar_url });
    }
  },
  {
    title: '用户',
    key: 'user_name',
    align: 'center',
    render(row) {
      return h('span', null, [row.user_name]);
    }
  },
  {
    title: '手机号',
    key: 'phone',
    align: 'center'
  },
  {
    title: '角色',
    key: 'role',
    align: 'center',
    render(row) {
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
          options: allRole.value[groupInfo.id],
          onSelect: (index, item) => selectRole(row, item),
        },
        h(
          NText,
          {
            type: 'info',
            style: `cursor:${allRole.value[groupInfo.id] ? 'pointer' : 'no-allowed'};color:${allRole.value[groupInfo.id] ? '' : 'grey'}`,
          },
          '添加角色'
        )
      );
      return row.role ? tag : dropList;
    },
  },
  {
    title: '操作',
    align: 'center',
    render(row, rowIndex) {
      return h(
        NButton,
        {
          tag: 'span',
          text: true,
          type: 'primary',
          disabled: storage.getValue('user_id') === String(row.user_id) || groupInfo.re_user_group_role_type !== 1,
          onClick: () => {
            if (storage.getValue('user_id') !== String(row.user_id) && groupInfo.re_user_group_role_type === 1) {
              groupUserDel(rowIndex);
            }
          },
        },
        ['删除']
      );
    }
  },
];

// change table page
function groupTurnPages(page) {
  groupPagination.page = page;
  getGroupUsers();
}

// change table pageSize
function groupTurnPageSize(pageSize) {
  groupPagination.pageSize = pageSize;
  groupPagination.page = 1;
  getGroupUsers();
}

//add user
const showAddUser = ref(false);
function addUser() {
  showAddUser.value = true;
}

export {
  tableLoading,
  showAddUser,
  usersColumns,
  groupInfo,
  groupPagination,
  allRole,
  getGroupRole,
  editGroupUsers,
  drawerUpdateShow,
  groupTurnPages,
  groupTurnPageSize,
  addUser,
};
