import { ref } from 'vue';
import axios from '@/axios';

import {
  handleSuccessSubmit,
  handleFailureSubmit,
} from './updateSubmitHandler.js';

const form = ref(null);

const model = ref({
  sockets: undefined,
  cores: undefined,
  threads: undefined,
});

const propsData = ref({
  id: undefined,
  name: undefined,
  sockets: undefined,
  cores: undefined,
  threads: undefined,
});

const initData = (data) => {
  propsData.value.id = data.id;
  propsData.value.name = data.name;
  propsData.value.sockets = data.sockets;
  propsData.value.cores = data.cores;
  propsData.value.threads = data.threads;
  model.value.sockets = data.sockets;
  model.value.cores = data.cores;
  model.value.threads = data.threads;
};

const onValidSubmit = (context) => {
  axios
    .put('/v1/vmachine', {
      id: propsData.value.id,
      sockets: model.value.sockets,
      cores: model.value.cores,
      threads: model.value.threads,
    })
    .then((res) => {
      if (res.error_code === '2000') {
        window.$notification?.success(
          handleSuccessSubmit(propsData.value.name, 'CPU配置', [
            {
              name: 'Sockets',
              curData: propsData.value.sockets,
              newData: model.value.sockets,
            },
            {
              name: 'Cores',
              curData: propsData.value.cores,
              newData: model.value.cores,
            },
            {
              name: 'Threads',
              curData: propsData.value.threads,
              newData: model.value.threads,
            },
          ])
        );
        context.emit('refresh');
      } else {
        window.$notification?.error(
          handleFailureSubmit(propsData.value.name, 'CPU配置', res.error_msg)
        );
      }
    })
    .catch((err) => {
      const mesg = err.data.validation_error.body_params[0].msg;
      window.$notification?.error(
        handleFailureSubmit(propsData.value.name, 'CPU配置', mesg)
      );
    });
};

export default {
  form,
  model,
  initData,
  onValidSubmit,
};

