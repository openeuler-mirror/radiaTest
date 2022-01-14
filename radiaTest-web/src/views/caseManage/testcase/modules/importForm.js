import { ref } from 'vue';
import axios from '@/axios';

const size = ref('medium');

const model = ref({
  group: undefined,
  framework: undefined,
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
  group: {
    required: true,
    message: '必须选择归属团队',
    trigger: ['blur'],
  },
  framework: {
    required: true,
    message: '必须选定测试框架',
    trigger: ['blur'],
  }
};

const getFrameworkOptions = () => {
  axios
    .get('/v1/framework')
    .then((res) => {
      if (!res.error_mesg) {
        frameworkOptions.value = res.map((item) => {
          return {
            label: item.name,
            value: item.name,
          };
        });
      } else {
        window.$message?.error(res.error_mesg);
      }
    })
    .catch(() => {
      window.$message?.error('获取框架数据失败，请检查网络或联系管理员处理');
    });
};

const getGroupOptions = () => {
  axios
    .get('/v1/groups')
    .then((res) => {
      groupOptions.value = res.data.items.map((item) => {
        return {
          label: item.name,
          value: item.name,
        };
      });
    })
    .catch(() => {
      window.$message?.error('无法获取所属团队信息，请检查网络或联系管理员处理');
    });
};

const initOptions = () => {
  getFrameworkOptions();
  getGroupOptions();
};

async function beforeUpload({ file }) {
  const matchList = file.file.name.match(/\..*$/);
  let fileType = null;
  matchList.length > 0 ? (fileType = matchList[matchList.length - 1]) : 0;
  if (
    fileType !== '.xlsx' &&
      fileType !== '.xls' &&
      fileType !== '.csv'
  ) {
    window.$message?.error(
      '只能上传xlsx、xls、csv格式的Excel文件，请重新上传'
    );
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


