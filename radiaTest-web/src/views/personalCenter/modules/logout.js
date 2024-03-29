import axios from '@/axios';
import { changeLoadingStatus } from '@/assets/utils/loading';
import router from '@/router';

function logout() {
  changeLoadingStatus(true);
  axios.delete('/v1/logout').then(res => {
    changeLoadingStatus(false);
    if (res.error_code === '2000') {
      window.sessionStorage.clear();
      router.replace({
        name: 'task'
      });

    }
  });
}

export {
  logout,
};
