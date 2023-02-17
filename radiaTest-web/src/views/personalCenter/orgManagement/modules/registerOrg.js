import { ref, reactive } from 'vue';
import { changeLoadingStatus } from '@/assets/utils/loading';
import axios from '@/axios';
import { getData } from './orgTable';
import { organizationInfo } from '@/api/put';

const showRegisterOrgWindow = ref(false);
const isCreate = ref(true);
function openRegisterOrgWindow() {
  isCreate.value = true;
  showRegisterOrgWindow.value = true;
}
const requireCla = ref(false);
const registerModel = reactive({
  name: null,
  claVerifyUrl: null,
  claSignUrl: null,
  claRequestMethod: null,
  claPassFlag: null,
  enterpriseId: null,
  enterpriseJoinUrl: null,
  urlParams: [],
  bodyParams: [],
  oauthClientId: null,
  oauthClientSecret: null,
  oauthClientScope: [],
  description: null,
  orgId: null,
  organizationAvatar: null,
  authorityType: 'gitee',
  authoritySecondaryType: 'public',
  oauthLoginUrl: null,
  oauthGetTokenUrl: null,
  oauthGetUserInfoUrl: null
});

const rules = {
  name: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入组织名'
  },
  claVerifyUrl: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入cla验证地址'
  },
  claSignUrl: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入cla签署地址'
  },
  claRequestMethod: {
    required: true,
    trigger: ['blur', 'change'],
    message: '请选择验证地址的请求方式'
  },
  enterpriseId: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入'
  },
  claPassFlag: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入cla验证通过的标志'
  },
  oauthLoginUrl: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入'
  },
  oauthClientId: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入'
  },
  oauthClientSecret: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入'
  },
  oauthClientScope: {
    required: true,
    type: 'array',
    trigger: ['blur', 'input'],
    message: '请填写',
    validator(rule, value) {
      if (value.length) {
        return true;
      }
      return false;
    }
  },
  oauthGetTokenUrl: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入'
  },
  oauthGetUserInfoUrl: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入'
  }
};
const regirsterRef = ref();
// 验证地址的请求方式
const requestOptions = [
  {
    label: 'GET',
    value: 'GET'
  },
  {
    label: 'POST',
    value: 'POST'
  },
  {
    label: 'PUT',
    value: 'PUT'
  },
  {
    label: 'OPTION',
    value: 'OPTION'
  }
];
const fileList = ref([]);

const claVerifyUrlChange = (data) => {
  if (!data) {
    registerModel.claRequestMethod = null;
  }
};

// 切换鉴权模式
function changeAuthorityType(value) {
  registerModel.authorityType = value;
  if (value === 'oneid') {
    registerModel.oauthClientScope = ['openid', 'profile'];
  }
}

function changeAuthoritySecondaryTypeGroup(value) {
  registerModel.authoritySecondaryType = value;
}

// 关闭表单
function closeOrgFrom() {
  showRegisterOrgWindow.value = false;
  fileList.value = [];
  registerModel.name = null;
  registerModel.description = null;
  registerModel.claVerifyUrl = null;
  registerModel.claSignUrl = null;
  registerModel.claPassFlag = null;
  registerModel.claRequestMethod = null;
  registerModel.urlParams = [];
  registerModel.bodyParams = [];
  registerModel.authorityType = 'gitee';
  registerModel.authoritySecondaryType = 'public';
  registerModel.oauthLoginUrl = null;
  registerModel.oauthClientId = null;
  registerModel.oauthClientSecret = null;
  registerModel.oauthClientScope = [];
  registerModel.oauthGetTokenUrl = null;
  registerModel.oauthGetUserInfoUrl = null;
  registerModel.enterpriseId = null;
  registerModel.enterpriseJoinUrl = null;
  registerModel.orgId = null;
  registerModel.organizationAvatar = null;
}

// 注册新组织
function handleCreateOrg(formData) {
  axios
    .post('/v1/admin/org', formData)
    .then((res) => {
      changeLoadingStatus(false);
      getData();
      if (res.error_code === '2000') {
        window.$message?.success('注册成功!');
      }
    })
    .catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
      changeLoadingStatus(false);
    })
    .finally(() => {
      closeOrgFrom();
    });
}

// 修改组织信息
function handleUpdateOrg(id, formData) {
  organizationInfo(id, formData).finally(() => {
    changeLoadingStatus(false);
    getData();
    closeOrgFrom();
  });
}

// 提交表单
function submitOrgInfo() {
  const [claVerifyBody, claVerifyParams] = [{}, {}];
  registerModel.urlParams.forEach((item) => {
    claVerifyParams[item.key] = item.value;
  });
  registerModel.bodyParams.forEach((item) => {
    claVerifyBody[item.key] = item.value;
  });

  let formData = new FormData();
  formData.append('avatar_url', fileList.value[0]?.file);
  formData.append('name', registerModel.name);
  formData.append('cla_verify_url', registerModel.claVerifyUrl);
  formData.append('cla_sign_url', registerModel.claSignUrl);
  formData.append('cla_request_type', registerModel.claRequestMethod);
  formData.append('cla_pass_flag', registerModel.claPassFlag);
  formData.append('cla_verify_params', JSON.stringify(claVerifyParams));
  formData.append('cla_verify_body', JSON.stringify(claVerifyBody));
  formData.append('description', registerModel.description);

  if (registerModel.authorityType === 'gitee' && registerModel.authoritySecondaryType === 'public') {
    formData.append('authority', 'default');
  } else if (registerModel.authorityType === 'oneid') {
    formData.append('authority', 'oneid');
    formData.append('oauth_login_url', registerModel.oauthLoginUrl);
    formData.append('oauth_client_id', registerModel.oauthClientId);
    formData.append('oauth_client_secret', registerModel.oauthClientSecret);
    formData.append('oauth_scope', registerModel.oauthClientScope?.join(','));
    formData.append('oauth_get_token_url', registerModel.oauthGetTokenUrl);
    formData.append('oauth_get_user_info_url', registerModel.oauthGetUserInfoUrl);
  } else if (registerModel.authorityType === 'gitee' && registerModel.authoritySecondaryType === 'personal') {
    formData.append('authority', 'gitee');
    formData.append('oauth_login_url', registerModel.oauthLoginUrl);
    formData.append('oauth_client_id', registerModel.oauthClientId);
    formData.append('oauth_client_secret', registerModel.oauthClientSecret);
    formData.append('oauth_scope', registerModel.oauthClientScope?.join(','));
    formData.append('oauth_get_token_url', registerModel.oauthGetTokenUrl);
    formData.append('oauth_get_user_info_url', registerModel.oauthGetUserInfoUrl);
  } else {
    formData.append('authority', 'gitee');
    formData.append('oauth_login_url', registerModel.oauthLoginUrl);
    formData.append('oauth_client_id', registerModel.oauthClientId);
    formData.append('oauth_client_secret', registerModel.oauthClientSecret);
    formData.append('oauth_scope', registerModel.oauthClientScope?.join(','));
    formData.append('oauth_get_token_url', registerModel.oauthGetTokenUrl);
    formData.append('oauth_get_user_info_url', registerModel.oauthGetUserInfoUrl);
    formData.append('enterprise_id', registerModel.enterpriseId);
    formData.append('enterprise_join_url', registerModel.enterpriseJoinUrl);
  }

  regirsterRef.value.validate((errors) => {
    if (!errors) {
      changeLoadingStatus(true);
      if (isCreate.value) {
        handleCreateOrg(formData);
      } else {
        formData.append('org_id', registerModel.orgId);
        handleUpdateOrg(registerModel.orgId, formData);
      }
    } else {
      window.$message?.error('请完善信息!');
    }
  });
}

function uploadFinish(options) {
  fileList.value = options;
}

export {
  rules,
  showRegisterOrgWindow,
  regirsterRef,
  requestOptions,
  registerModel,
  openRegisterOrgWindow,
  submitOrgInfo,
  fileList,
  closeOrgFrom,
  handleCreateOrg,
  handleUpdateOrg,
  uploadFinish,
  requireCla,
  isCreate,
  changeAuthorityType,
  changeAuthoritySecondaryTypeGroup,
  claVerifyUrlChange
};
