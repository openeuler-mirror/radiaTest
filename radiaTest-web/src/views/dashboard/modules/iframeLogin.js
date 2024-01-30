import { urlArgs } from '@/assets/utils/urlUtils';
import { storage } from '@/assets/utils/storageUtils';
function iframeLogin() {
  const { isIframe, value } = urlArgs();
  if (isIframe && isIframe === '1') {
    console.log('调用了iframeLogin', iframeLogin);
    const { orgId, url, token, giteeId } = JSON.parse(decodeURIComponent(value));
    storage.setValue('isIframe', isIframe);
    storage.setValue('token', token);
    storage.setValue('loginOrgId', orgId);
    storage.setValue('user_id', giteeId);
    if (url) {
      window.location = url;
    }
  } else {
    console.log('没有调用iframelogin', isIframe, value);
  }
}

export {
  iframeLogin
};
