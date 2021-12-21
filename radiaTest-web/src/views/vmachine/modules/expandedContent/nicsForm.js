import { ref } from 'vue';

const formRef = ref(null);

const formValue = ref({
  vmachine_id: null,
  bus: undefined,
  mode: undefined,
  mac: undefined,
});

const initData = (machineId) => {
  formValue.value.vmachine_id = machineId;
};

const validateFormData = (context) => {
  formRef.value.validate((error) => {
    if (error) {
      window.$message?.error('请检查输入合法性');
    } else {
      context.emit('valid');
    }
  });
};

const clean = () => {
  formValue.value = {
    vmachine_id: null,
    bus: undefined,
    mode: undefined,
    mac: undefined,
  };
};

export default {
  formRef,
  formValue,
  initData,
  validateFormData,
  clean,
};
  
