import { ref, computed } from 'vue';

const size = ref('medium');

const formRef = ref(null);
const formValue = ref({
  name: undefined,
  version: undefined,
  description: undefined,
});

const clean = () => {
  formValue.value = {
    name: null,
    version: null,
    description: null,
  };
};

const defaultOptions = [
  {
    label: 'openEuler',
    value: 'openEuler',
  },
  {
    label: 'CentOS',
    value: 'CentOS',
  },
  {
    label: 'fedora',
    value: 'fedora',
  },
  {
    label: 'Ubuntu',
    value: 'Ubuntu',
  },
  {
    label: 'debian',
    value: 'debian',
  },
  {
    label: 'openSUSE',
    value: 'openSUSE',
  },
  {
    label: 'arch',
    value: 'arch',
  },
];

const nameOptions = computed(() => [
  {
    label: formValue.value.name,
    value: formValue.value.name,
  },
  ...defaultOptions,
]);

const rules = ref({
  name: {
    required: true,
    message: '版本全称不可为空',
    trigger: ['blur'],
  },
  version: {
    required: true,
    message: '版本全称不可为空',
    trigger: ['blur'],
  },
});

export default {
  size,
  rules,
  formRef,
  nameOptions,
  formValue,
  clean,
};

