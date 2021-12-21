import { ref } from 'vue';

const size = ref('medium');

const contentFormRef = ref(null);

const contentFormValue = ref({});

const clean = () => {
  contentFormValue.value = {};
};

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

const initData = (data) => {
  contentFormValue.value = JSON.parse(JSON.stringify(data));
};

export default {
  size,
  contentRules,
  contentFormRef,
  contentFormValue,
  clean,
  initData,
};
