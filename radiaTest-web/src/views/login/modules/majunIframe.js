import { ref } from 'vue';

import axios from '@/axios';
import router from '@/router/index';
import { storage } from '@/assets/utils/storageUtils';
import { urlArgs } from '@/assets/utils/urlUtils';

const route = urlArgs();

const regCancel = ref(true);
const isFrame = route.isIftrame;
function isIframe () {
  if (isFrame) {
    console.log('iframe');
    regCancel.value = false;
    window.hideLogout = true;
    window.addEventListener('message', e => {
      if (typeof e.data === 'string') {
        axios.post('/v1/majun/login', { access_token: e.data }).then(res => {
          if (res.error_code === '4010') {
            e.source.postMessage({
              isSuccess: 'False',
              gitee_id: res.data.gitee_id,
            }, 'http://192.168.0.114:8084');
          } else {
            storage.setValue('token', res.data.token);
            storage.setValue('refresh_token', res.data.refresh_token);
            storage.setValue('gitee_id', res.data.gitee_id);
            router.push({ name: 'home' });
          }
        });
      }
    }, false);
  }
}

export {
  regCancel,
  isFrame,
  isIframe,
};
