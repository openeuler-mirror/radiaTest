import { ref, computed } from 'vue';
import { getSuite } from '@/api/get';

const size = ref('medium');

const diskUsage = ref(null);

const infoFormRef = ref(null);

const infoFormValue = ref({});

const suiteOptions = ref([]);

const initSuiteOptions = () => {
  getSuite()
    .then((res) => {
      suiteOptions.value = res.data.map((item) => {
        return {
          label: item.name,
          value: item.name
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
    }
  ];
});

const clean = () => {
  infoFormValue.value = {};
};

const infoRules = ref({
  name: {
    required: true,
    message: '用例名不可为空',
    trigger: ['blur']
  },
  suite: {
    required: true,
    message: '所属测试套不可为空',
    trigger: ['blur']
  },
  owner: {
    required: true,
    message: '责任人不可为空',
    trigger: ['blur']
  },
  add_disk: {
    trigger: ['change', 'blur'],
    validator(rule, value) {
      if (value && !value.every((item) => item.match(/^[0-9]* GiB$/))) {
        return new Error('存在非法格式的磁盘');
      }
      return true;
    }
  }
});

const initData = (data) => {
  infoFormValue.value = data;
  data.add_disk
    ? (infoFormValue.value.add_disk = data.add_disk.split(',').map((item) => `${item} GiB`))
    : (infoFormValue.value.add_disk = []);
};

export default {
  size,
  infoRules,
  infoFormRef,
  suiteOptions,
  infoFormValue,
  diskUsage,
  clean,
  initSuiteOptions,
  usageOptions,
  initData
};
