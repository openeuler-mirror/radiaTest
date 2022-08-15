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
const requireEnterprise = ref(false);
const requireCla = ref(false);
const registerModel = reactive({
  name: undefined,
  claVerifyUrl: undefined,
  claSignUrl: undefined,
  claRequestMethod: undefined,
  claPassFlag: undefined,
  enterpriseId: undefined,
  enterpreiseJoinUrl: undefined,
  urlParams: [],
  bodyParams: [],
  oauthClientId: undefined,
  oauthClientSecret: undefined,
  oauthClientScope: [],
  description: undefined,
  orgId: undefined,
  organizationAvatar: undefined,
});

const rules = {
  name: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入组织名',
  },
  claVerifyUrl: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入cla验证地址',
  },
  claSignUrl: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入cla签署地址',
  },
  claRequestMethod: {
    required: true,
    trigger: ['blur', 'change'],
    message: '请选择验证地址的请求方式',
  },
  enterpriseId: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入',
  },
  claPassFlag: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入cla验证通过的标志',
  },
  oauthClientId: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入',
  },
  oauthClientSecret: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入',
  },
  oauthClientScope: {
    trigger: ['blur', 'input'],
    message: '请填写',
    validator(rule, value) {
      if (value.length) {
        return true;
      }
      return false;
    },
  },
};
const regirsterRef = ref();
const requestOptions = [
  {
    label: 'GET',
    value: 'GET',
  },
  {
    label: 'POST',
    value: 'POST',
  },
  {
    label: 'PUT',
    value: 'PUT',
  },
  {
    label: 'OPTION',
    value: 'OPTION',
  },
];
const fileList = ref([]);

function closeOrgFrom() {
  showRegisterOrgWindow.value = false;
  fileList.value = [];

  registerModel.name = undefined;
  registerModel.claVerifyUrl = undefined;
  registerModel.claSignUrl = undefined;
  registerModel.claRequestMethod = undefined;
  registerModel.claPassFlag = undefined;
  registerModel.enterpriseId = undefined;
  registerModel.enterpreiseJoinUrl = undefined;
  registerModel.urlParams = [];
  registerModel.bodyParams = [];
  registerModel.oauthClientId = undefined;
  registerModel.oauthClientSecret = undefined;
  registerModel.oauthClientScope = undefined;
  registerModel.description = undefined;
  registerModel.orgId = undefined; 
  registerModel.organizationAvatar = undefined;
}

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

function handleUpdateOrg(id, formData) {
  organizationInfo(id, formData)
    .finally(() => {
      changeLoadingStatus(false);
      getData();
      closeOrgFrom();
    });
}

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
  formData.append('enterprise_id', registerModel.enterpriseId);
  formData.append('enterprise_join_url', registerModel.enterpreiseJoinUrl);
  formData.append('oauth_client_id', registerModel.oauthClientId);
  formData.append('oauth_client_secret', registerModel.oauthClientSecret);
  formData.append('oauth_scope', registerModel.oauthClientScope?.join(','));
  formData.append('description', registerModel.description);

  regirsterRef.value.validate((errors) => {
    if (!errors) {
      changeLoadingStatus(true);
      if(isCreate.value){
        handleCreateOrg(formData);
      }else{
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
  requireEnterprise,
  fileList,
  closeOrgFrom,
  handleCreateOrg,
  handleUpdateOrg,
  uploadFinish,
  requireCla,
  isCreate,
};
