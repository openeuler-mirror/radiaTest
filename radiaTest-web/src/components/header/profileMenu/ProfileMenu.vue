<template>
  <n-grid :cols="16">
    <n-gi :span="2"> </n-gi>
    <n-gi :span="7" style="display: flex; align-items: center">
      <n-gradient-text type="primary">{{ currentOrg }}</n-gradient-text>
      <n-divider vertical />
      <n-gradient-text type="info">{{ accountName }}</n-gradient-text>
    </n-gi>
    <n-gi :span="2">
      <div class="msg-box">
        <n-badge :value="msgCount" style="cursor: pointer" @click="gotoNews">
          <n-icon :size="40" :color="msgCount ? '' : '#9b9b9b'">
            <bell-outlined />
          </n-icon>
        </n-badge>
      </div>
    </n-gi>
    <n-gi :span="1"> </n-gi>
    <n-gi :span="4">
      <n-dropdown
        trigger="hover"
        @select="handleSelect"
        :options="options"
        size="huge"
        :show-arrow="true"
        placement="bottom-end"
      >
        <n-avatar
          style="position: relative; left: 10px; cursor: pointer"
          circle
          :size="60"
          :src="avatarUrl"
        />
      </n-dropdown>
    </n-gi>
  </n-grid>
  <n-modal
    v-model:show="showOrgModal"
    preset="dialog"
    :showIcon="false"
    title="Dialog"
  >
    <template #header>
      <div>切换组织</div>
    </template>
    <n-form-item
      label="组织"
      label-placement="left"
      :lable-width="80"
      :rule="orgRule"
    >
      <n-select
        v-model:value="activeOrg"
        :options="orgOptions"
        placeholder="请选择组织"
      ></n-select>
    </n-form-item>
    <template #action>
      <n-button @click="switchOrg" type="primary" ghost size="large"
        >确定</n-button
      >
    </template>
  </n-modal>
</template>

<script>
import { defineComponent, getCurrentInstance, inject, watch } from 'vue';
import { BellOutlined } from '@vicons/antd';
import { modules } from './modules/index.js';

export default defineComponent({
  components: {
    BellOutlined
  },
  setup() {
    const { proxy } = getCurrentInstance();
    modules.getOrg();
    const msgCount = inject('msgCount');
    const msgCountUpdate = inject('msgCountUpdate');
    watch(msgCount, (newVal, oldVal) => {
      if (newVal > oldVal) {
        document.dispatchEvent(new CustomEvent('reloadNews'));
        proxy.$axios.get('/v1/msg', { has_read: 0, page_num: 1, page_size: 10 }).then(res => {
          proxy.$store.commit('news/setUnreadNewsList', res.data.items);
        });
        proxy.$axios.get('/v1/msg', { has_read: 1, page_num: 1, page_size: 10 }).then(res => {
          proxy.$store.commit('news/setReadNewsList', res.data.items);
        });
      }
    }, {
      deep: true,
    });

    return {
      msgCount,
      msgCountUpdate,
      ...modules,
    };
  },
});
</script>

<style scoped lang="less">
.msg-box {
  display: flex;
  align-items: center;
  height: 100%;
}
</style>
