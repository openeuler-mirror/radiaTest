import { ref } from 'vue';
import axios from '@/axios';

const size = ref('medium');

const model = ref({
  suite: undefined,
});
const fileListRef = ref([]);

const clean = () => {
  model.value.suite = undefined;
  fileListRef.value = [];
};

const formRef = ref(null);
const uploadRef = ref(null);

const suiteOptions = ref([]);

const rules = {
  suite: {
    required: true,
    message: '必须选择一个测试套以绑定',
    trigger: ['blur'],
  },
};

const initSuiteOptions = () => {
  axios
    .get('/v1/suite')
    .then((res) => {
      if (!res.error_mesg) {
        suiteOptions.value = res.map((item) => {
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
      window.$message?.error('获取数据失败，请检查网络或联系管理员处理');
    });
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
  suiteOptions,
  initSuiteOptions,
  uploadRef,
  beforeUpload,
  validateFormData,
  clean,
};


