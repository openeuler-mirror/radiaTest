import { reactive, h, ref } from 'vue';
import { NAvatar, NButton, NSpace } from 'naive-ui';

import { changeLoadingStatus } from '@/assets/utils/loading';
import { state, activeIndex } from './groupTable';
import { storage } from '@/assets/utils/storageUtils';
import axios from '@/axios';

//drawer base information
const groupInfo = reactive({
  name: '',
  usersData: [],
  id: '',
  show: false,
  re_user_group_role_type: '',
});
const groupPagination = reactive({
  pageSize: 5,
  page: 1,
  pageCount: 1,
  itemCount: 1,
});

// get table data
function getGroupUsers () {
  changeLoadingStatus(true);
  axios.get(`/v1/groups/${groupInfo.id}/users`, {
    page_num: groupPagination.page,
    page_size: groupPagination.pageSize
  }).then(res => {
    changeLoadingStatus(false);
    groupInfo.usersData = res.data.items;
    groupInfo.show = true;
    groupPagination.pageCount = res.data.pages;
    groupPagination.itemCount = res.data.total;
  }).catch((err) => {
    window.$message?.error(err.data.error_msg || '未知错误');
    changeLoadingStatus(false);
  });
}


function editGroupUsers (rowIndex) {
  groupInfo.name = state.dataList[rowIndex].groupName;
  groupInfo.id = state.dataList[rowIndex].id;
  groupInfo.re_user_group_id = state.dataList[rowIndex].re_user_group_id;
  groupInfo.re_user_group_role_type = state.dataList[rowIndex].re_user_group_role_type;
  getGroupUsers();
}
function drawerUpdateShow (show) {
  groupInfo.show = show;
}
function groupUserDel (rowIndex) {
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
                gitee_ids: [groupInfo.usersData[rowIndex].gitee_id],
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
  state.dataList[activeIndex].users.splice(rowIndex, 1);
}

//drawer-table columns
const usersColumns = [
  {
    title: '',
    key: 'avatar_url',
    align: 'center',
    render (row) {
      return h(NAvatar, { size: 'small', src: row.avatar_url });
    }
  },
  {
    title: '用户',
    key: 'gitee_name',
    align: 'center',
    render (row) {
      return h('span', null, [row.gitee_name]);
    }
  },
  {
    title: '手机号',
    key: 'phone',
    align: 'center'
  },
  {
    title: '操作',
    align: 'center',
    render (row, rowIndex) {
      return h(
        NButton,
        {
          tag: 'span',
          text: true,
          type: 'primary',
          disabled: storage.getValue('gitee_id') === String(row.gitee_id),
          onClick: () => {
            if (storage.getValue('gitee_id') !== String(row.gitee_id)) {
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
function groupTurnPages (page) {
  groupPagination.page = page;
  getGroupUsers();
}

//add user
const showAddUser = ref(false);
function addUser () {
  showAddUser.value = true;
}

export {
  showAddUser,
  usersColumns,
  groupInfo,
  groupPagination,
  editGroupUsers,
  drawerUpdateShow,
  groupTurnPages,
  addUser,
};
