import { ref, reactive } from 'vue';

import axios from '@/axios';
import { changeLoadingStatus } from '@/assets/utils/loading';
import { getDataList } from './groupTable';

const showCreateForm = ref(false);
const formRef = ref();
const createModal = reactive({
  name: '',
  description: ''
});
const rules = {
  name: {
    required: true,
    trigger: ['blur', 'input'],
    message: '请输入组织名'
  }
};
const fileList = ref([]);
function createGroup() {
  showCreateForm.value = true;
}
function onNegativeClick() {
  window.$message && window.$message.info('取消创建');
  showCreateForm.value = false;
}
async function onPositiveClick() {
  await formRef.value.validate((errors) => {
    if (!errors) {
      changeLoadingStatus(true);
      let formData = new FormData();
      formData.append('avatar_url', fileList.value[0]?.file);
      formData.append('name', createModal.name);
      formData.append('description', createModal.description);
      axios.post('/v1/groups', formData).then(() => {
        showCreateForm.value = false;
        createModal.name = '';
        createModal.description = '';
        fileList.value = [];
        window.$message && window.$message.success('添加成功!');
        getDataList();
      }).catch((err) => {
        window.$message && window.$message.error(err.data.error_msg);
        showCreateForm.value = false;
        changeLoadingStatus(false);
      });

    } else {
      window.$message && window.$message.error('请输入完整信息');
      showCreateForm.value = true;
    }
  });
  return false;
}
function uploadFinish(options) {
  fileList.value = options;
}

export {
  formRef,
  rules,
  createModal,
  fileList,
  showCreateForm,
  createGroup,
  onNegativeClick,
  onPositiveClick,
  uploadFinish,
};
