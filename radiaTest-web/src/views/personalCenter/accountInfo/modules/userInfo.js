import { reactive, ref } from 'vue';

import { changeLoadingStatus } from '@/assets/utils/loading';
import axios from '@/axios';
import { storage } from '@/assets/utils/storageUtils';

const state = reactive({
  userInfo: {}
});
const isEditPhone = ref(false);
const phone = ref('');
function editUserPhone () {
  if (isEditPhone.value === true) {
    const phoneReg = /^[1]([3-9])[0-9]{9}$/;
    if (phoneReg.test(phone.value)) {
      changeLoadingStatus(true);
      axios.put(`/v1/users/${storage.getValue('gitee_id')}`, {
        phone: phone.value
      }).then(res => {
        if (res.error_code === '2000') {
          window.$message?.success('修改成功!');
        }
        isEditPhone.value = !isEditPhone.value;
        state.userInfo.phone = phone.value;
        changeLoadingStatus(false);
      }).catch((err) => {
        window.$message?.error(err.data.error_msg||'未知错误');
        changeLoadingStatus(false);
      });
    } else {
      window.$message?.error('手机号不合法');
    }
  } else {
    isEditPhone.value = !isEditPhone.value;
  }
}
function cancelEditPhone () {
  phone.value = '';
  isEditPhone.value = false;
}

export {
  state,
  phone,
  isEditPhone,
  editUserPhone,
  cancelEditPhone,
};
