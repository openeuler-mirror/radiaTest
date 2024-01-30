import { ref } from 'vue';
import axios from '@/axios';
import { getFramework } from './frameworkTable';
import { storage } from '@/assets/utils/storageUtils';

const isCreate = ref(true);
const showModal = ref(false);

const frameworkForm = ref({
  name: '',
  url: '',
  logs_path: '',
  adaptive: false,
});
const frameworkRules = {
  name: {
    trigger: ['blur', 'input'],
    message: '名称必填',
    required: true,
  },
  logs_path: {
    trigger: ['blur', 'input'],
    required: true,
    validator(rule, value) {
      if (!value) {
        return new Error('日志路径必填');
      } else if (/^\//.test(value)) {
        return new Error('日志路径格式有误!请填写相对路径');
      }
      return true;
    },
  },
  url: {
    trigger: ['blur', 'input'],
    required: true,
    validator(rule, value) {
      if (!value) {
        return new Error('仓库地址必填');
      } else if (
        !/^http(s)?:\/\/[a-z0-9-]+(.[a-z0-9-]+)*(:[0-9]+)?(\/.*)?$/.test(value)
      ) {
        return new Error('仓库地址格式有误!');
      }
      return true;
    },
  },
};
const formRef = ref();
let editFramework;
function changeFramework(value) {
  editFramework = value;
}
function closeForm() {
  showModal.value = false;
  frameworkForm.value = {
    name: '',
    url: '',
    logs_path: '',
    adaptive: false,
  };
}
function submitForm() {
  formRef.value?.validate((error) => {
    if (!error) {
      const url = isCreate.value
        ? '/v1/framework'
        : `/v1/framework/${editFramework}`;
      const formData = JSON.parse(JSON.stringify(frameworkForm.value));
      if (isCreate.value) {
        formData.creator_id = storage.getValue('user_id');
        formData.permission_type = 'public';
        formData.org_id = storage.getValue('loginOrgId');
      }
      axios[isCreate.value ? 'post' : 'put'](url, formData)
        .then(() => {
          getFramework();
          window.$message?.success(isCreate.value ? '创建成功' : '修改成功');
        })
        .catch((err) => {
          window.$message?.error(err.data.error_msg || '未知错误');
        });
      closeForm();
    } else {
      window.$message?.error('填写信息有误,请检查!');
    }
  });
}
function showForm() {
  showModal.value = true;
}
function addFramework() {
  isCreate.value = true;
  showForm();
}
function deleteFramework(id) {
  axios
    .delete(`/v1/framework/${id}`)
    .then(() => {
      window.$message?.success('删除成功');
      getFramework();
    })
    .catch((err) => window.$message?.error(err.data.error_msg || '未知错误'));
}
export {
  formRef,
  frameworkRules,
  showModal,
  isCreate,
  frameworkForm,
  addFramework,
  closeForm,
  submitForm,
  showForm,
  deleteFramework,
  changeFramework,
};
