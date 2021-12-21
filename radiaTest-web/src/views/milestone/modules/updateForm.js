import { ref } from 'vue';

const formRef = ref(null);
const formValue = ref({});

const init = (data) => {
  formValue.value = data;
};

export default {
  formRef,
  formValue,
  init,
};
