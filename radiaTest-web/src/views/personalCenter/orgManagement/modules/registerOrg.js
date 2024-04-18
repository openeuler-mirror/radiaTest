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
});

const rules = {
  name: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入组织名'
  },


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
  requireCla.value = false;
  fileList.value = [];
  registerModel.name = null;
  registerModel.description = null;
}

// 注册新组织
function handleCreateOrg(formData) {
  axios
    .post('/v1/admin/org', formData, {
      headers: {
        'Content-Type': 'multipart/form-data'
      }
    })
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
  let formData = new FormData();
  formData.append('avatar_url', fileList.value[0]?.file);
  formData.append('name', registerModel.name);
  formData.append('description', registerModel.description);
  formData.append('authority', 'default');

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
