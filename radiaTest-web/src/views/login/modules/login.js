
import router from '@/router/index';
import { storage } from '@/assets/utils/storageUtils';
import { addRoom } from '@/assets/utils/socketUtils';
import { urlArgs, } from '@/assets/utils/urlUtils';

import { loginByCode } from '@/api/get';
function handleIsSuccess() {
  if (urlArgs().isSuccess === 'True') {
    setTimeout(() => {
      router.push({ name: 'task' }).then(() => {
        addRoom(storage.getValue('token'));
      });
    }, 1000);
  } else if (urlArgs().isSuccess === 'False') {
    router.push({ name: 'task' });
  }
}

// 进入登录页面
function gotoHome() {
  if (urlArgs().code) {
    loginByCode({
      code: urlArgs().code,
      org_id: storage.getValue('loginOrgId')
    }).then((res) => {
      storage.setValue('token', res.data?.token);
      storage.setValue('user_id', res.data?.user_id);
      storage.setLocalValue('unLoginOrgId', {
        name: res.data?.current_org_name,
        id: res.data?.current_org_id
      });
      window.location = res.data?.url; // login?isSuccess=True
    });
  }
  handleIsSuccess();
}


export {
  gotoHome,
  handleIsSuccess,
};
