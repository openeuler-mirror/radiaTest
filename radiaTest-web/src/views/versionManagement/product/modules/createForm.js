import { ref } from 'vue';
import { getGroup } from '@/api/get';

const size = ref('medium');

const formRef = ref(null);
const formValue = ref({
  name: undefined,
  version: undefined,
  permission_type: null,
  version_type: '',
  is_forced_check: true,
  description: undefined
});

const clean = () => {
  formValue.value = {
    name: null,
    version: null,
    permission_type: null,
    version_type: '',
    is_forced_check: true,
    description: null
  };
};

const rules = ref({
  name: {
    required: true,
    message: '版本全称不可为空',
    trigger: ['blur']
  },
  version: {
    required: true,
    message: '版本全称不可为空',
    trigger: ['blur']
  },
  permission_type: {
    required: true,
    message: '请选择类型',
    trigger: ['change', 'blur']
  },
  version_type: {
    required: true,
    message: '请选择版本类型',
    trigger: ['change', 'blur']
  }
});
const typeOptions = ref([
  { label: '公共', value: 'public', isLeaf: true },
  { label: '组织', value: 'org', isLeaf: true },
  { label: '团队', value: 'group', isLeaf: false },
  { label: '个人', value: 'person', isLeaf: true }
]);
function handleLoad(option) {
  return new Promise((resolve, reject) => {
    getGroup({ page_num: 1, page_size: 99999 })
      .then((res) => {
        option.children = res.data.items.map((item) => ({
          label: item.name,
          value: `group-${item.id}`
        }));
        resolve();
      })
      .catch((err) => reject(err));
  });
}

export default {
  size,
  rules,
  typeOptions,
  handleLoad,
  formRef,
  formValue,
  clean
};
