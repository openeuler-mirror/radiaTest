import { urlArgs } from '@/assets/utils/urlUtils';
import { storage } from '@/assets/utils/storageUtils';
function iframeLogin() {
  const { isIframe, value } = urlArgs();
  if(isIframe && isIframe === '1') {
    const { orgId, url, token, giteeId } = JSON.parse(decodeURIComponent(value));
    storage.setValue('isIframe', isIframe);
    token && storage.setValue('token', token);
    orgId && storage.setValue('loginOrgId', orgId);
    giteeId && storage.setValue('user_id', giteeId);
    if(url) {
      window.location = url;
    }
  }
}

export {
  iframeLogin
};
