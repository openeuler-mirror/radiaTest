import { ref } from 'vue';
const repoModal = ref(false);
const isRepoCreate = ref(false);
import { createRepo } from '@/api/post';
import { modifyRepo } from '@/api/put';
import { getRepo } from './frameworkTable';
import { storage } from '@/assets/utils/storageUtils';
import router from '@/router';
const repoRef = ref();
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
let modifyRepoId;
let modifyRepoInfo;
function setModifyRepo(id, info) {
  modifyRepoId = id;
  modifyRepoInfo = info;
}
const repoForm = ref({
  name: '',
  git_url: '',
  sync_rule: false,
  framework_id: '',
});
function showRepoModal() {
  repoModal.value = true;
}
function clearRepoForm() {
  repoForm.value = {
    name: '',
    git_url: '',
    sync_rule: false,
    framework_id: '',
  };
}
function closeRepoForm() {
  clearRepoForm();
  repoModal.value = false;
}
function submitRepoForm() {
  repoRef.value?.validate((errors) => {
    if (!errors) {
      if (isRepoCreate.value) {
        createRepo({
          ...repoForm.value,
          creator_id: storage.getValue('gitee_id'),
          permission_type: 'group',
          group_id: router.currentRoute.value.query.id,
          org_id: storage.getValue('loginOrgId'),
        }).then(() => {
          getRepo(modifyRepoInfo);
          closeRepoForm();
        });
      } else {
        modifyRepo(modifyRepoId, repoForm.value).then(() => {
          getRepo(modifyRepoInfo);
          closeRepoForm();
        });
      }
    } else {
      window.$message?.error('填写信息有误,请检查!');
    }
  });
}

export {
  repoRules,
  repoModal,
  repoForm,
  repoRef,
  isRepoCreate,
  closeRepoForm,
  showRepoModal,
  submitRepoForm,
  clearRepoForm,
  setModifyRepo,
};
