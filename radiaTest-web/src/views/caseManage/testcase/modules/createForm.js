import { ref, computed } from 'vue';
import axios from '@/axios';
import { workspace } from '@/assets/config/menu.js';

const size = ref('medium');

const tab = ref('basic');

const diskUsage = ref(null);

const infoFormRef = ref(null);
const contentFormRef = ref(null);

const infoFormValue = ref({
  suite: undefined,
  name: undefined,
  test_level: undefined,
  test_type: undefined,
  machine_num: undefined,
  machine_type: undefined,
  owner: undefined,
  add_network_interface: undefined,
  add_disk: undefined,
  automatic: undefined,
  remark: undefined,
});

const contentFormValue = ref({
  description: undefined,
  preset: undefined,
  steps: undefined,
  expection: undefined,
});

const suiteOptions = ref([]);

const initSuiteOptions = () => {
  axios
    .get(`/v1/ws/${workspace.value}/suite`)
    .then((res) => {
      suiteOptions.value = res.data.map((item) => {
        return {
          label: item.name,
          value: item.name,
        };
      });
    })
    .catch(() => {
      window.$message?.error('获取数据失败，请检查网络或联系管理员处理');
    });
};

const usageOptions = computed(() => {
  if (diskUsage.value === null) {
    return [];
  }
  return [
    {
      label: `${diskUsage.value} GiB`,
      value: `${diskUsage.value} GiB`
    },
  ];
});

const clean = () => {
  infoFormValue.value = {
    suite: undefined,
    name: undefined,
    test_level: undefined,
    test_type: undefined,
    machine_num: undefined,
    machine_type: undefined,
    owner: undefined,
    add_network_interface: undefined,
    add_disk: undefined,
    automatic: undefined,
    remark: undefined,
  };
  contentFormValue.value = {
    description: undefined,
    preset: undefined,
    steps: undefined,
    expection: undefined,
  };
  tab.value = 'basic';
};

const infoRules = ref({
  name: {
    required: true,
    message: '用例名不可为空',
    trigger: ['blur'],
  },
  suite: {
    required: true,
    message: '所属测试套不可为空',
    trigger: ['blur'],
  },
  owner: {
    required: true,
    message: '责任人不可为空',
    trigger: ['blur'],
  },
  add_disk: {
    trigger: ['change', 'blur'],
    validator (rule, value) {
      if (value && !value.every(item => item.match(/^[0-9]* GiB$/))) {
        return new Error('存在非法格式的磁盘');
      }
      return true;
    }
  }
});

const contentRules = ref({
  description: {
    required: true,
    message: '用例描述不可为空',
    trigger: ['blur'],
  },
  steps: {
    required: true,
    message: '用例步骤不可为空',
    trigger: ['blur'],
  },
  expection: {
    required: true,
    message: '用例预期结果不可为空',
    trigger: ['blur'],
  },
});

const validateFormData = (context) => {
  infoFormRef.value.validate((infoError) => {
    contentFormRef.value.validate((contentError) => {
      if (infoError || contentError) {
        window.$message?.error('请检查输入合法性');
      } else {
        context.emit('valid');
      }
    });
  });
};

export default {
  size,
  tab,
  infoRules,
  contentRules,
  infoFormRef,
  contentFormRef,
  suiteOptions,
  infoFormValue,
  contentFormValue,
  diskUsage,
  clean,
  initSuiteOptions,
  usageOptions,
  validateFormData,
};
