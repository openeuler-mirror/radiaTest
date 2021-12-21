import { ref } from 'vue';

const tabValue = ref('aarch64');
const loading = ref(false);
const repo = ref({
  aarch64: {},
  x86_64: {},
});
const edit = ref({
  aarch64: false,
  x86_64: false,
});
const content = ref({
  aarch64: '',
  x86_64: '',
});

const clean = () => {
  tabValue.value = 'aarch64';
  repo.value = {
    aarch64: {},
    x86_64: {},
  };
  edit.value = {
    aarch64: false,
    x86_64: false,
  };
  content.value = {
    aarch64: '',
    x86_64: '',
  };
};

export default {
  tabValue,
  loading,
  repo,
  edit,
  content,
  clean,
};
