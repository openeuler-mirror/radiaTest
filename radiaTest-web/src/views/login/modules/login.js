import { reactive, ref, h } from 'vue';

import axios from '@/axios';
import router from '@/router/index';
import { storage } from '@/assets/utils/storageUtils';
import { addRoom } from '@/assets/utils/socketUtils';
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
  passWord: ''
});
const rules = {
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

const loginFormRef = ref();
function handleLoginByForm() {
  loginFormRef.value.validate((error) => {
    if (!error) {
      changeLoadingStatus(true);
      axios
        .post('/v1/admin/login', {
          account: loginForm.userName,
          password: loginForm.passWord
        })
        .then((res) => {
          changeLoadingStatus(false);
          if (res?.data) {
            storage.setValue('token', res.data.token);
            storage.setValue('role', 1);
            storage.setValue('account', res.data.account);
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

function requireEnterprise(orgid) {
  const activeOrg = orgOpts.value.find((item) => item.value === orgid);
  if (activeOrg) {
    return activeOrg.enterprise;
  }
  return false;
}

// 组织登录按钮
function hanleLogin(orgId) {
  changeLoadingStatus(true);
  storage.setValue('loginOrgId', Number(orgId));
  storage.setValue('hasEnterprise', requireEnterprise(orgId));
  const isIframe = storage.getValue('isIframe');
  axios
    .get('/v1/oauth/login', { org_id: Number(orgId) })
    .then((res) => {
      if (res?.data) {
        const giteeUrl = res.data;
        changeLoadingStatus(false);
        if (isIframe && isIframe === '1') {
          window.parent.postMessage(
            {
              giteeUrl
            },
            '*'
          );
        } else {
          window.location = giteeUrl;
        }
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
function handleIsSuccess() {
  if (urlArgs().isSuccess === 'True') {
    setTimeout(() => {
      registerShow.value = false;
      router.push({ name: 'home' }).then(() => {
        addRoom(storage.getValue('token'));
      });
    }, 1000);
  } else if (urlArgs().isSuccess === 'False') {
    loginInfo.org = urlArgs().org_id;
    registerShow.value = true;
    requireCLA.value = urlArgs().require_cla === 'True';
    getClaOrg();
  }
}

// 进入登录页面
function gotoHome() {
  orgListLoading.value = true;
  getAllOrg().then((res) => {
    orgOpts.value = res.data.map((item) => ({
      label: item.org_name,
      value: String(item.org_id),
      ...item
    }));
    orgListLoading.value = false;
  });
  if (urlArgs().code) {
    loginByCode({
      code: urlArgs().code,
      org_id: storage.getValue('loginOrgId')
    }).then((res) => {
      storage.setValue('token', res.data?.token);
      storage.setValue('user_id', res.data?.user_id);
      window.location = res.data?.url; // login?isSuccess=True
    });
  }
  handleIsSuccess();
}
function renderLabel(option) {
  return h(
    'div',
    {
      style: {
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        width: '100%'
      }
    },
    [
      h(NAvatar, {
        src: option.org_avatar,
        round: false,
        size: 'small',
        style: 'margin-right:10px',
        fallbackSrc: createAvatar(option.label.slice(0, 1))
      }),
      option.label
    ]
  );
}

const authorityType = ref('gitee');
const selecttdOrg = ref({});

function selectOrg(value) {
  const org = orgOpts.value.find((item) => item.value === value);
  selecttdOrg.value = org;
  hasCLA.value = org.cla;
  hasEnterprise.value = org.enterprise;
  loginOrg.value = org.value;
  claSignUrl.value = org.cla_sign_url ? org.cla_sign_url : undefined;
  enterpriseJoinUrl.value = org.enterprise_join_url ? org.enterprise_join_url : undefined;
  if (org.authority === 'gitee') {
    authorityType.value = 'gitee';
  } else {
    authorityType.value = 'oneid';
  }
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
  handleIsSuccess,
  loginOrg,
  orgOpts,
  renderLabel,
  selectOrg,
  handleClaSignClick,
  handleEnterpriseJoinClick,
  authorityType,
  selecttdOrg
};
