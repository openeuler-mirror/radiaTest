import { ref } from 'vue';
import router from '@/router';
import axios from '@/axios';
const repoModal = ref(false);
const frameworkList = ref([]);
const repoRef1 = ref();
import { setGroupRepo } from '@/api/post.js';
import { getCodeData } from './repoTable.js';
const repoRules = {
  name: {
    trigger: ['blur', 'input'],
    message: '名称必填',
    required: true,
  },
  git_url: {
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

const repoForm = ref({
  framework_id: '',
  name: '',
  git_url: '',
  sync_rule: false,
  is_adapt: false
});

function getFrameworkOptions() {
  axios.get('/v1/framework').then(res => {
    frameworkList.value = res.data?.map(item => ({ label: item.name, value: item.id }));
  });
}

function showRepoModal() {
  getFrameworkOptions();
  repoModal.value = true;
}


function clearRepoForm() {
  repoForm.value = {
    framework_id: '',
    name: '',
    git_url: '',
    sync_rule: false,
    is_adapt: false
  };
}

function closeRepoForm() {
  clearRepoForm();
  repoModal.value = false;
}

function submitRepoForm() {
  repoRef1.value?.validate((errors) => {
    if (!errors) {
      setGroupRepo({
        ...repoForm.value,
        group_id: router.currentRoute.value.query.id
      }).then(() => {
        closeRepoForm();
        getCodeData();
      });
    } else {
      window.$message?.error('填写信息有误,请检查!');
    }
  });
}

export {
  repoModal,
  repoForm,
  frameworkList,
  repoRules,
  repoRef1,
  closeRepoForm,
  submitRepoForm,
  showRepoModal
};
