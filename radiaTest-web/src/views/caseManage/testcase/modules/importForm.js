import { ref } from 'vue';
import axios from '@/axios';
import { getGroup } from '@/api/get';
import { workspace } from '@/assets/config/menu.js';

const size = ref('medium');

const model = ref({
  group_id: undefined,
  framework_id: undefined,
});
const fileListRef = ref([]);

const clean = () => {
  model.value.group = undefined;
  model.value.framework = undefined;
  fileListRef.value = [];
};

const formRef = ref(null);
const uploadRef = ref(null);

const groupOptions = ref([]);
const frameworkOptions = ref([]);

const rules = {
  group_id: {
    required: true,
    message: '必须选择归属团队',
    trigger: ['blur'],
  },
  framework_id: {
    required: true,
    message: '必须选定测试框架',
    trigger: ['blur'],
  },
};

const getFrameworkOptions = () => {
  axios
    .get(`/v1/ws/${workspace.value}/framework`)
    .then((res) => {
      frameworkOptions.value = res.data?.map((item) => {
        return {
          label: item.name,
          value: String(item.id),
        };
      });
    })
    .catch(() => {
      window.$message?.error('获取框架数据失败，请检查网络或联系管理员处理');
    });
};

const getGroupOptions = () => {
  getGroup({
    page_size: 99999,
    page_num: 1,
  })
    .then((res) => {
      groupOptions.value = res.data.items.map((item) => {
        return {
          label: item.name,
          value: String(item.id),
        };
      });
    })
    .catch(() => {
      window.$message?.error(
        '无法获取所属团队信息，请检查网络或联系管理员处理'
      );
    });
};

const initOptions = () => {
  getFrameworkOptions();
  getGroupOptions();
};

async function beforeUpload({ file }) {
  console.log('file', file, file.file.size);
  let matchList = file.file.name.split('.');
  let fileType = matchList[matchList.length - 1];
  const supportedFiletypes = ['xlsx', 'xls', 'csv', 'md', 'markdown'];
  if (!supportedFiletypes.includes(fileType)) {
    window.$message?.error('只能上传xlsx、xls、csv、md、markdown格式的文件，请重新上传');
    return false;
  }
  return true;
}

const validateFormData = (context) => {
  formRef.value.validate((error) => {
    if (error) {
      window.$message?.error('请检查输入合法性');
    } else {
      context.emit('valid');
    }
  });
};

const handleUploadChange = ({ fileList }) => {
  fileListRef.value = fileList;
};

export default {
  size,
  rules,
  fileListRef,
  handleUploadChange,
  model,
  formRef,
  groupOptions,
  frameworkOptions,
  initOptions,
  uploadRef,
  beforeUpload,
  validateFormData,
  clean,
};
