<template>
  <n-grid :cols="13">
    <n-gi :span="7" v-if="isIframe && isIframe === '1'"></n-gi>
    <n-gi :span="7" v-else style="display: flex; align-items: center">
      <n-gradient-text type="primary">{{ currentOrg }}</n-gradient-text>
      <n-divider vertical />
      <n-gradient-text type="info">{{ accountName }}</n-gradient-text>
    </n-gi>
    <n-gi :span="2">
      <div class="msg-box">
        <n-badge :value="msgCount" style="cursor: pointer" @click="gotoNews">
          <n-icon :size="30" :color="msgCount ? '' : '#9b9b9b'">
            <bell-outlined />
          </n-icon>
        </n-badge>
      </div>
    </n-gi>
    <n-gi :span="4">
      <n-dropdown
        trigger="hover"
        @select="handleSelect"
        :options="isIframe && isIframe === '1' ? iframeOptions : options"
        size="huge"
        :show-arrow="true"
        placement="bottom-end"
      >
        <n-avatar
          class="profile-avatar"
          circle
          :fallback-src="createAvatar(accountName.slice(0, 1))"
          :size="40"
          :src="avatarUrl"
        />
      </n-dropdown>
    </n-gi>
  </n-grid>
</template>

<script>
import { defineComponent, getCurrentInstance, inject, watch } from 'vue';
import { BellOutlined } from '@vicons/antd';
import { modules } from './modules/index.js';
import { createAvatar } from '@/assets/utils/createImg';
import { storage } from '@/assets/utils/storageUtils';
export default defineComponent({
  components: {
    BellOutlined
  },
  setup() {
    const { proxy } = getCurrentInstance();
    modules.getOrg();
    const msgCount = inject('msgCount');
    const isIframe = storage.getValue('isIframe');
    watch(
      msgCount,
      () => {
        document.dispatchEvent(new CustomEvent('reloadNews'));
        proxy.$axios.get('/v1/msg', { has_read: 0, page_num: 1, page_size: 10 }).then((res) => {
          proxy.$store.commit('news/setUnreadNewsList', res.data.items);
        });
        proxy.$axios.get('/v1/msg', { has_read: 1, page_num: 1, page_size: 10 }).then((res) => {
          proxy.$store.commit('news/setReadNewsList', res.data.items);
        });
      },
      {
        deep: true
      }
    );

    return {
      msgCount,
      isIframe,
      createAvatar,
      ...modules
    };
  }
});
</script>

<style scoped lang="less">
.msg-box {
  display: flex;
  align-items: center;
  height: 100%;
}

.profile-avatar {
  cursor: pointer;
  display: flex;
  align-items: center;
}
</style>
