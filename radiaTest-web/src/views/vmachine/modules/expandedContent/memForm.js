import { ref } from 'vue';
import axios from '@/axios';

import {
  handleSuccessSubmit,
  handleFailureSubmit,
} from './updateSubmitHandler.js';

const form = ref(null);

const model = ref({
  memory: undefined,
});

const propsData = ref({
  id: undefined,
  name: undefined,
  memory: undefined,
});

const initData = (data) => {
  model.value.memory = data.memory;
  propsData.value.id = data.id;
  propsData.value.name = data.name;
  propsData.value.memory = data.memory;
};

const onValidSubmit = (context) => {
  axios
    .put(`/v1/vmachine/${propsData.value.id}`, {
      memory: model.value.memory,
    })
    .then((res) => {
      if (res.error_code === '2000') {
        window.$notification?.success(
          handleSuccessSubmit(propsData.value.name, '内存', [
            {
              name: 'Memory',
              curData: propsData.value.memory,
              newData: model.value.memory,
            },
          ])
        );
        context.emit('refresh');
      } else {
        window.$notification?.error(
          handleFailureSubmit(propsData.value.name, '内存', res.error_msg)
        );
      }
    })
    .catch((err) => {
      const mesg = err.data.validation_error.body_params[0].msg;
      window.$notification?.error(
        handleFailureSubmit(propsData.value.name, '内存', mesg)
      );
    });
};

export default {
  form,
  model,
  initData,
  onValidSubmit,
};

