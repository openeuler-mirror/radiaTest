<template>
  <div class="login-page">
    <n-result status="info" title="登录" description="正在奋力登录中......"> </n-result>
  </div>
</template>
<script setup>
import router from '@/router/index';
import { storage } from '@/assets/utils/storageUtils';
import { addRoom } from '@/assets/utils/socketUtils';
import { urlArgs } from '@/assets/utils/urlUtils';
import { loginByCode } from '@/api/get';

const handleIsSuccess = () => {
  if (urlArgs().isSuccess === 'True') {
    setTimeout(() => {
      router.push({ name: 'task' }).then(() => {
        addRoom(storage.getValue('token'));
      });
    }, 1000);
  } else if (urlArgs().isSuccess === 'False') {
    router.push({ name: 'task' });
  }
};

// 进入登录页面
const gotoHome = () => {
  if (urlArgs().code) {
    loginByCode({
      code: urlArgs().code,
      org_id: storage.getValue('loginOrgId'),
    }).then((res) => {
      storage.setValue('token', res.data?.token);
      storage.setValue('user_id', res.data?.user_id);
      storage.setLocalValue('unLoginOrgId', {
        name: res.data?.current_org_name,
        id: res.data?.current_org_id,
      });
      window.location = res.data?.url; // login?isSuccess=True
    });
  }
  handleIsSuccess();
};
onMounted(() => {
  gotoHome();
});
</script>
<style lang="less">
.login-page {
  height: 100%;
  display: flex;
  justify-content: center;
  align-items: center;
}
</style>
