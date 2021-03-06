import { reactive, ref, h } from 'vue';

import axios from '@/axios';
import router from '@/router/index';
import { storage } from '@/assets/utils/storageUtils';
import { addRoom } from '@/assets/utils/socketUtils';
import { getCookieValByKey } from '@/assets/utils/cookieUtils';
import { urlArgs, openChildWindow } from '@/assets/utils/urlUtils';
import { changeLoadingStatus } from '@/assets/utils/loading';
import { getClaOrg } from './org';
import { getAllOrg, loginByCode } from '@/api/get';
import { NAvatar } from 'naive-ui';
import { loginInfo } from './claSign';
import { createAvatar } from '@/assets/utils/createImg';

const loginOrg = ref(null);
const orgOpts = ref([]);
const requireCLA = ref(true);
const hasCLA = ref(false);
const hasEnterprise = ref(false);
const claSignUrl = ref();
const enterpriseJoinUrl = ref();
const orgListLoading = ref(false);
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
  },
};

const loginFormRef = ref();
function handleLoginByForm () {
  loginFormRef.value.validate((error) => {
    if (!error) {
      changeLoadingStatus(true);
      axios
        .post('/v1/admin/login', {
          account: loginForm.userName,
          password: loginForm.passWord,
        })
        .then((res) => {
          changeLoadingStatus(false);
          if (res?.data) {
            storage.setValue('token', res.data.token);
            storage.setValue('refresh_token', res.data.refresh_token);
            storage.setValue('role', 1);
            router.push({ name: 'orgManagement' });
          }
        })
        .catch((err) => {
          window.$message?.error(err.data.error_msg || '未知错误');
          changeLoadingStatus(false);
        });
    } else {
      window.$message?.error('验证失败');
    }
  });
}

function requireEnterprise (orgid) {
  const activeOrg = orgOpts.value.find(item => item.value === orgid);
  if (activeOrg) {
    return activeOrg.enterprise;
  }
  return false;
}
function hanleLogin () {
  changeLoadingStatus(true);
  storage.setValue('loginOrgId', Number(loginOrg.value));
  storage.setValue('hasEnterprise', requireEnterprise(loginOrg.value));
  axios
    .get('/v1/gitee/oauth/login', { org_id: Number(loginOrg.value) })
    .then((res) => {
      if (res?.data) {
        const giteeUrl = res.data;
        changeLoadingStatus(false);
        window.location = giteeUrl;
      } else {
        changeLoadingStatus(false);
        throw new Error(res.error_msg);
      }
    })
    .catch((err) => {
      changeLoadingStatus(false);
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

const registerShow = ref(false);
function gotoHome () {
  orgListLoading.value = true;
  getAllOrg().then((res) => {
    orgOpts.value = res.data.map((item) => ({
      label: item.org_name,
      value: String(item.org_id),
      ...item,
    }));
    orgListLoading.value = false;
  });
  if (urlArgs().code) {
    loginByCode({
      code: urlArgs().code,
      org_id: storage.getValue('loginOrgId'),
    }).then((res) => {
      storage.setValue('token', getCookieValByKey('token'));
      storage.setValue('refresh_token', getCookieValByKey('refresh_token'));
      storage.setValue('gitee_id', getCookieValByKey('gitee_id'));
      window.location = res.data;
    });
  }
  if (urlArgs().isSuccess === 'True') {
    setTimeout(() => {
      registerShow.value = false;
      storage.setValue('token', getCookieValByKey('token'));
      storage.setValue('refresh_token', getCookieValByKey('refresh_token'));
      storage.setValue('gitee_id', getCookieValByKey('gitee_id'));
      router.push({ name: 'home' })
        .then(
          () => {
            addRoom(storage.getValue('token'));
          }
        );
    }, 1000);
  } else if (urlArgs().isSuccess === 'False') {
    loginInfo.org = urlArgs().org_id;
    registerShow.value = true;
    requireCLA.value = urlArgs().require_cla === 'True';
    getClaOrg();
  }
}
function renderLabel (option) {
  return h(
    'div',
    {
      style: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: '100%',
      },
    },
    [
      h(NAvatar, {
        src: option.org_avatar,
        round: false,
        size: 'small',
        style: 'margin-right:10px',
        fallbackSrc: createAvatar(option.label.slice(0, 1))
      }),
      option.label,
    ]
  );
}
function selectOrg (value) {
  const org = orgOpts.value.find((item) => item.value === value);
  hasCLA.value = org.cla;
  hasEnterprise.value = org.enterprise;
  loginOrg.value = org.value;
  claSignUrl.value = org.cla_sign_url ? org.cla_sign_url : undefined;
  enterpriseJoinUrl.value = org.enterprise_join_url ? org.enterprise_join_url : undefined;
}
function handleClaSignClick() {
  if (claSignUrl.value) {
    openChildWindow(claSignUrl.value);
  } else {
    window.message?.error('该组织CLA签署地址已缺失');
  }
}
function handleEnterpriseJoinClick() {
  if (enterpriseJoinUrl.value) {
    openChildWindow(enterpriseJoinUrl.value);
  } else {
    window.message?.info('该组织没有公开的企业仓加入指引/入口');
  }
}

export {
  requireCLA,
  orgListLoading,
  rules,
  hasCLA,
  hasEnterprise,
  loginForm,
  loginFormRef,
  registerShow,
  handleLoginByForm,
  hanleLogin,
  gotoHome,
  loginOrg,
  orgOpts,
  renderLabel,
  selectOrg,
  handleClaSignClick,
  handleEnterpriseJoinClick,
};
