<template>
  <n-spin :show="showLoading" stroke="rgba(0, 47, 167, 1)">
    <div>
      <div class="accountInfo-header">
        <n-avatar
          style="position: absolute; top: 50%; z-index: 999"
          circle
          :size="100"
          :src="state.userInfo.avatar_url"
          :fallback-src="createAvatar(String(state.userInfo.user_name).slice(0, 1))"
        />
      </div>
      <div class="container">
        <h3 class="item-title">基本信息</h3>
        <div class="info-item">
          <n-grid :cols="12">
            <n-gi :span="1">
              <p>用户名</p>
            </n-gi>
            <n-gi :span="2">
              <p>{{ state.userInfo.user_name }}</p>
            </n-gi>
            <n-gi :span="9">
              <p>
                <n-button quaternary type="info" @click="handlePrivacyClick">
                  取消隐私协议
                </n-button>
              </p>
            </n-gi>
          </n-grid>
        </div>
      </div>
    </div>
  </n-spin>
</template>
<script>
import { createAvatar } from '@/assets/utils/createImg';
import { modules } from './modules/index.js';

export default {
  setup() {
    modules.init();

    document.addEventListener('reloadInfo', () => {
      modules.init();
    });
    return { ...modules, createAvatar };
  },
  unmounted() {
    modules.allRole.value = {};
  },
};
</script>
<style lang="less" scoped>
.info-item {
  margin: 10px 0;
}
.accountInfo-header {
  height: 100px;
  width: 100%;
  text-align: center;
  background-color: rgba(155, 155, 155, 0.2);
  position: relative;
}

.container {
  padding: 10px 50px;
  margin-top: 10px;
}

.title {
  margin-bottom: 10px;
}

.item-title {
  margin: 5px 0;
}

.info-item {
  margin: 10px 0;

  .info-item-box {
    align-items: center;
  }
}

.info-operation-btn {
  margin: 0 5px;
}

.msg-box {
  height: 100%;
  display: flex;
  justify-content: flex-end;
  align-items: center;
}
</style>
