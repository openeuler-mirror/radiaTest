import { reactive, ref } from 'vue';

import axios from '@/axios';
import router from '@/router/index';
import { storage } from '@/assets/utils/storageUtils';
import { getCookieValByKey } from '@/assets/utils/cookieUtils';
import { urlArgs } from '@/assets/utils/urlUtils';
import { changeLoadingStatus } from '@/assets/utils/loading';
import { getClaOrg } from './org';

const loginForm = reactive({
  userName: '',
  passWord: '',
});
const rules = {
  userName: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入用户名',
  },
  passWord: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入密码',
  }
};

const loginFormRef = ref();
function handleLoginByForm () {
  loginFormRef.value.validate((error) => {
    if (!error) {
      changeLoadingStatus(true);
      axios.post('/v1/admin/login', { account: loginForm.userName, password: loginForm.passWord }).then(res => {
        changeLoadingStatus(false);
        if (res?.data) {
          storage.setValue('token', res.data.token);
          storage.setValue('refresh_token', res.data.refresh_token);
          storage.setValue('role', 1);
          router.push({ name: 'orgManagement' });
        }
      }).catch((err) => {
        window.$message?.error(err.data.error_msg || '未知错误');
        changeLoadingStatus(false);
      });
    } else {
      window.$message?.error('验证失败');
    }
  });
}

function hanleLogin () {
  changeLoadingStatus(true);
  axios.get('/v1/gitee/oauth/login').then(res => {
    if (res?.data) {
      const giteeUrl = res.data;
      changeLoadingStatus(false);
      window.location = giteeUrl;
    } else {
      changeLoadingStatus(false);
      throw new Error(res.error_msg);
    }
  }).catch(err => {
    changeLoadingStatus(false);
    window.$message?.error(err.data.error_msg || '未知错误');
  });
}

const registerShow = ref(false);
function gotoHome () {
  if (urlArgs().isSuccess === 'True') {
    setTimeout(() => {
      registerShow.value = false;
      storage.setValue('token', getCookieValByKey('token'));
      storage.setValue('refresh_token', getCookieValByKey('refresh_token'));
      storage.setValue('gitee_id', getCookieValByKey('gitee_id'));
      router.push({ name: 'home' });
    }, 1000);
  } else if (urlArgs().isSuccess === 'False') {
    registerShow.value = true;
    getClaOrg();
  }
}

export {
  rules,
  loginForm,
  loginFormRef,
  registerShow,
  handleLoginByForm,
  hanleLogin,
  gotoHome,
};
