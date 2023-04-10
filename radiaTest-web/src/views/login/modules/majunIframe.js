import { ref } from 'vue';

import axios from '@/axios';
import router from '@/router/index';
import { addRoom } from '@/assets/utils/socketUtils';
import { storage } from '@/assets/utils/storageUtils';
import { urlArgs } from '@/assets/utils/urlUtils';

const route = urlArgs();

const regCancel = ref(true);
const isFrame = route.isIftrame;
function isIframe () {
  if (isFrame) {
    regCancel.value = false;
    window.hideLogout = true;
    window.addEventListener('message', e => {
      if (typeof e.data === 'string') {
        axios.post('/v1/majun/login', { access_token: e.data }).then(res => {
          if (res.error_code === '4010') {
            e.source.postMessage({
              isSuccess: 'False',
              user_id: res.data.user_id,
            }, 'http://192.168.0.114:8084');
          } else {
            storage.setValue('token', res.data.token);
            storage.setValue('refresh_token', res.data.refresh_token);
            storage.setValue('user_id', res.data.user_id);
            router.push({ name: 'home' })
              .then(
                () => {
                  addRoom(storage.getValue('token'));
                }
              );
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
