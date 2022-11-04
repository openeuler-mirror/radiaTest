import { hanleLogin, gotoHome } from '@/views/login/modules/login';
import { urlArgs } from '@/assets/utils/urlUtils';
import { storage } from '@/assets/utils/storageUtils';

function thirdPartLogin() {
  const { orgId, code, thirdParty } = urlArgs();
  if(thirdParty) {
    storage.setValue('thirdParty', thirdParty);
    if(code) {
      gotoHome();
    } else {
      hanleLogin(orgId);
    }
  }
}

export {
  thirdPartLogin
};
