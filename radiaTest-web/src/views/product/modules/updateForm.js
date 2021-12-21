import { ref } from 'vue';

const formRef = ref(null);
const formValue = ref({});

const rules =  {
  name: {
    required: true,
    message: '产品名不可为空',
  },
  version: {
    required: true,
    message: '版本名不可为空',
  },
};

const init = (data) => {
  formValue.value = data;
};


export default {
  rules,
  formRef,
  formValue,
  init,
};

