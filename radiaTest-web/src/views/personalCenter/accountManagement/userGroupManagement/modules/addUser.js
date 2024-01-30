import { ref, reactive, computed } from 'vue';

import axios from '@/axios';
// import { storage } from '@/assets/utils/storageUtils';
import { changeLoadingStatus } from '@/assets/utils/loading';
import { groupInfo, showAddUser } from './groupDrawer';

let addUserInfo = reactive({
  name: '',
  value: ''
});
const usersList = ref([]);
function deleteItems(index) {
  usersList.value.splice(index, 1);
}
function searchUser() {

}
function initAddInfo() {
  usersList.value = [];
  addUserInfo.name = '';
  addUserInfo.value = '';
}
function cancelAdd() {
  showAddUser.value = !showAddUser.value;
  initAddInfo();
}
function handlePositiveClick() {
  if (usersList.value.length) {
    changeLoadingStatus(true);
    const userIds = usersList.value.map(item => {
      return item.user_id;
    });
    axios.post(`/v1/groups/${groupInfo.id}/users`, {
      user_ids: userIds
    }).then(res => {
      changeLoadingStatus(false);
      if (res.error_code === '2000') {
        window.$message?.success('已向用户发送信息!');
      }
      cancelAdd();
    }).catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
      changeLoadingStatus(false);
    });
  } else {
    window.$message.error('不能提交空数据!');
  }
  return false;
}
const options = computed(() => {
  return usersList.value.map((info) => {
    return {
      label: info.user_name,
      key: info.user_id,
      value: info.user_id,
    };
  });
});

export {
  options,
  usersList,
  addUserInfo,
  searchUser,
  deleteItems,
  cancelAdd,
  handlePositiveClick,
};
