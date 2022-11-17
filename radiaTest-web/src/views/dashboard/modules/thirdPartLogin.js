import { hanleLogin } from '@/views/login/modules/login';
import { urlArgs } from '@/assets/utils/urlUtils';
import { storage } from '@/assets/utils/storageUtils';
import { initData } from './dashboard';

function getThirdPartMessage(val) {
  const params = val.data;
  console.log('接收传到的值：', params);
  if(params.orgId) {
    hanleLogin(params.orgId);
  }
  if(params.url) {
    storage.setValue('token', params.token);
    storage.setValue('gitee_id', params.giteeId);
    window.location = params.url;
  }
}

function thirdPartLogin() {
  const { thirdParty, orgId } = urlArgs();
  if(thirdParty && thirdParty === '1') {
    storage.setValue('thirdParty', thirdParty);
    if(orgId) {
      hanleLogin(orgId);
    }
    window.addEventListener('message', e => {
      getThirdPartMessage(e);
    });
  } else {
    initData();
  }
}

export {
  thirdPartLogin,
  getThirdPartMessage
};
