import { ref, reactive } from 'vue';

import { changeLoadingStatus } from '@/assets/utils/loading';
import axios from '@/axios';
import { getData } from './orgTable';

const showRegisterOrgWindow = ref(false);
function openRegisterOrgWindow () {
  showRegisterOrgWindow.value = true;
}

const registerModel = reactive({
  name: '',
  claVerifyUrl: '',
  claSignUrl: '',
  claRequestMethod: '',
  claPassFlag: '',
  enterprise:'',
  urlParams: [],
  bodyParams: []
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
  enterprise: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入',
  },
  claPassFlag: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入cla验证通过的标志',
  }
};
const regirsterRef = ref();
const requestOptions = [
  {
    label: 'GET',
    value: 'GET'
  }, {
    label: 'POST',
    value: 'POST'
  }, {
    label: 'PUT',
    value: 'PUT'
  }, {
    label: 'OPTION',
    value: 'OPTION'
  },
];
function submitOrgInfo () {
  const [claVerifyBody, claVerifyParams] = [{}, {}];
  registerModel.urlParams.forEach(item => {
    claVerifyParams[item.key] = item.value;
  });
  registerModel.bodyParams.forEach(item => {
    claVerifyBody[item.key] = item.value;
  });
  const data = {
    name: registerModel.name,
    cla_verify_url: registerModel.claVerifyUrl,
    cla_sign_url: registerModel.claSignUrl,
    cla_request_type: registerModel.claRequestMethod,
    cla_pass_flag: registerModel.claPassFlag,
    cla_verify_params: JSON.stringify(claVerifyParams),
    cla_verify_body: JSON.stringify(claVerifyBody),
    enterprise: registerModel.enterprise,
  };
  regirsterRef.value.validate(errors => {
    if (!errors) {
      changeLoadingStatus(true);
      axios.post('/v1/admin/org', data).then(res => {
        changeLoadingStatus(false);
        getData();
        if (res.error_code === '2000') {
          window.$message?.success('注册成功!');
        }
        showRegisterOrgWindow.value = false;
      }).catch((err) => {
        window.$message?.error(err.data.error_msg||'未知错误');
        changeLoadingStatus(false);
      });
    } else {
      window.$message?.error('请完善信息!');
    }
  });

}

export {
  rules,
  showRegisterOrgWindow,
  regirsterRef,
  requestOptions,
  registerModel,
  openRegisterOrgWindow,
  submitOrgInfo,
};
