import { h, ref } from 'vue';
import { NIcon } from 'naive-ui';
import { HomeOutlined } from '@vicons/antd';
import { LogInOutline } from '@vicons/ionicons5';
import { Login } from '@vicons/tabler';

import { activeOrg, getOrg, selectedOrg, currentOrg } from './orgInfo';
import axios from '@/axios';
import router from '@/router/index';
import { storage } from '@/assets/utils/storageUtils';
import store from '@/store';

const optionsLogined = [
  {
    label: '用户中心',
    key: 'accountInfo',
    icon() {
      return h(NIcon, null, {
        default: () => h(HomeOutlined)
      });
    }
  },

  {
    label: '退出登录',
    key: 'exit',
    props: {
      style: {
        display: window.hideLogout ? 'none' : ''
      }
    },
    icon() {
      return h(NIcon, null, {
        default: () => h(LogInOutline)
      });
    }
  }
];
const optionsUnLogin = [
  {
    label: '登录',
    key: 'orgLogin',
    icon() {
      return h(NIcon, null, {
        default: () => h(Login)
      });
    }
  },
  {
    label: '管理员登录',
    key: 'adminLogin',
    icon() {
      return h(NIcon, null, {
        default: () => h(Login)
      });
    },
  },

];

const iframeOptions = [
  {
    label: '用户中心',
    key: 'accountInfo',
    icon() {
      return h(NIcon, null, {
        default: () => h(HomeOutlined)
      });
    }
  }
];

const orgRule = {
  trigger: ['blur', 'change'],
  validator() {
    if (activeOrg.value) {
      return true;
    }
    return new Error('组织不能为空');
  }
};
const showOrgModal = ref(false);

function handleSelect(key) {
  if (key === 'accountManagement') {
    getOrg();
    showOrgModal.value = true;
  } else if (key === 'exit') {
    axios.delete('/v1/logout').then((res) => {
      if (res.error_code === '2000') {
        window.sessionStorage.clear();
        if (res.error_msg) {
          window.location = res.error_msg;
        } else if (router.currentRoute.value.matched[0].name === 'PersonalCenter') {
          router.replace({
            name: 'task'
          });
        } else {
          router.replace(`/blank?redirect=${router.currentRoute.value.fullPath}`);
        }

      }
    });
  } else if (key === 'accountInfo') {
    router.push({ name: key });
  } else if (key === 'orgLogin') {
    if (!selectedOrg.value) {
      window.$message?.warning('请选择登录方式！');
    } else {
      hanleLogin(selectedOrg.value.id);
    }
  } else if (key === 'adminLogin') {
    showLoginModal.value = true;
  }
}
function hanleLogin(orgId) {
  storage.setValue('loginOrgId', Number(orgId));
  axios
    .get('/v1/oauth/login', { org_id: Number(orgId) })
    .then((res) => {
      if (res?.data) {
        const giteeUrl = res.data;
        window.location = giteeUrl;
      } else {
        throw new Error(res.error_msg);
      }
    })
    .catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

const showLoginModal = ref(false);
const loginFormRef = ref(null);
const loginForm = reactive({
  userName: '',
  passWord: ''
});
const loginFormRules = {
  userName: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入用户名'
  },
  passWord: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入密码'
  }
};

function handleLoginByForm() {
  loginFormRef.value.validate((error) => {
    if (!error) {
      axios
        .post('/v1/admin/login', {
          account: loginForm.userName,
          password: loginForm.passWord
        })
        .then((res) => {
          if (res?.data) {
            storage.setValue('token', res.data.token);
            storage.setValue('account', res.data.account);
            showLoginModal.value = false;
            if (res.data.password_need_reset === 1) {
              storage.setValue('role', 'resetPassword');
              router.push({ name: 'securitySetting' });
            } else {
              storage.setValue('role', 1);
              router.push({ name: 'orgManagement' });
            }
          }
        })
        .catch((err) => {
          window.$message?.error(err.data.error_msg || '未知错误');
        });
    } else {
      window.$message?.error('验证失败');
    }
  });
}
function handleUpdateOrgValue(value) {
  selectedOrg.value = value;
  storage.setLocalValue('unLoginOrgId', value);
  store.commit('unLoginOrgId/setOrgId', value);
  router.replace(`/blank?redirect=${router.currentRoute.value.fullPath}`);
}

function handleUpdateLoginedOrg(value) {
  axios.put(`/v1/users/org/${value.id}/${value.name}`).then((res) => {
    if (res.error_msg === 'OK') {
      selectedOrg.value = value;
      storage.setLocalValue('unLoginOrgId', value);
      store.commit('unLoginOrgId/setOrgId', value);
      router.replace(`/blank?redirect=${router.currentRoute.value.fullPath}`);
    }
  }).catch((err) => {
    selectedOrg.value = {
      name: currentOrg.value || storage.getLocalValue('unLoginOrgId')?.name,
      id: activeOrg.value || storage.getLocalValue('unLoginOrgId')?.id,
    };
    window.$message?.error(err.data.error_msg || '未知错误');
  });
}
function handleFalse() {
  return false;
}

export {
  optionsLogined, optionsUnLogin, iframeOptions, orgRule, showOrgModal, handleSelect,
  handleLoginByForm, loginForm, showLoginModal, loginFormRules, loginFormRef, handleUpdateOrgValue,
  handleUpdateLoginedOrg, handleFalse
};
