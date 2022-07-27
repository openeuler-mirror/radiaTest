import { ref } from 'vue';

const size = ref('medium');

const thisFiletype = ref(undefined);
const formRef = ref(undefined);
const formValue = ref({
  id: undefined,
  url: undefined,
  ks: undefined,
  efi: undefined,
  location: undefined,
  user: undefined,
  port: undefined,
  password: undefined,
  milestone_id: undefined,
  frame: undefined,
});

const passwordValidate = (rule, value) => {
  if (thisFiletype.value === 'qcow2' && !value) {
    return new Error('ssh密码不可为空');
  } 
  return true;
};

const rules = ref({
  url: {
    required: true,
    message: 'URL不可为空',
    trigger: ['blur'],
  },
  password: {
    validator: passwordValidate,
    trigger: ['blur'],
  },
});

const clean = () => {
  formValue.value = {
    id: undefined,
    url: undefined,
    ks: undefined,
    efi: undefined,
    location: undefined,
    user: undefined,
    port: undefined,
    password: undefined,
    milestone_id: undefined,
    frame: undefined,
  };
};

export default {
  size,
  thisFiletype,
  formRef,
  formValue,
  rules,
  clean,
};
