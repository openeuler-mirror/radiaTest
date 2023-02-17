import { hanleLogin } from '@/views/login/modules/login';
import { urlArgs } from '@/assets/utils/urlUtils';
import { storage } from '@/assets/utils/storageUtils';
import { initData } from './dashboard';

function getIframeMessage(val) {
  const params = val ? val.data : {};
  if(params.orgId) {
    hanleLogin(params.orgId);
  }
  if(params.url) {
    storage.setValue('token', params.token);
    storage.setValue('user_id', params.userId);
    window.location = params.url;
  }
}

function iframeLogin() {
  const { isIframe, orgId } = urlArgs();
  if(isIframe && isIframe === '1') {
    storage.setValue('isIframe', isIframe);
    window.hideLogout = true;
    if(orgId) {
      hanleLogin(orgId);
    }
    window.addEventListener('message', e => {
      getIframeMessage(e);
    });
  } else {
    initData();
  }
}

export {
  iframeLogin,
  getIframeMessage
};
