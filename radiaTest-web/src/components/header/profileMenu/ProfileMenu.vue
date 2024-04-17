<template>
  <n-grid :cols="token ? 13 : 9">
    <n-gi :span="7" v-if="token" style="display: flex; align-items: center">
      <div>
        <n-popselect
          v-model:value="selectedOrg"
          @update:value="handleUpdateLoginedOrg"
          :options="orgListoptions"
          trigger="click"
        >
          <n-button quaternary icon-placement="right" strong secondary type="info"
            >{{ selectedOrg.name || '请选择登录' }}
            <template #icon>
              <n-icon>
                <cash-icon />
              </n-icon>
            </template>
          </n-button>
        </n-popselect>

        <n-divider vertical />
        <n-gradient-text type="info">{{ accountName }}</n-gradient-text>
      </div>
    </n-gi>
    <n-gi :span="3" v-else style="display: flex; align-items: center">
      <div>
        <n-popselect
          v-model:value="selectedOrg"
          @update:value="handleUpdateOrgValue"
          :options="orgListoptions"
          trigger="click"
        >
          <n-button quaternary icon-placement="right" strong secondary type="info"
            >{{ selectedOrg.name || '请选择登录' }}
            <template #icon>
              <n-icon>
                <cash-icon />
              </n-icon>
            </template>
          </n-button>
        </n-popselect>
      </div>
    </n-gi>
    <n-gi :span="token ? 2 : 1">
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
        :options="token ? optionsLogined : optionsUnLogin"
        size="huge"
        :show-arrow="true"
        placement="bottom-end"
      >
        <n-avatar
          v-if="token"
          class="profile-avatar"
          circle
          :fallback-src="createAvatar(accountName.slice(0, 1))"
          :size="40"
          :src="avatarUrl"
        />
        <div v-else class="text-login">登录</div>
      </n-dropdown>
    </n-gi>
  </n-grid>
  <n-modal v-model:show="showLoginModal" preset="dialog" :showIcon="false" :mask-closable="false">
    <div style="text-align: center; font-size: 24px">
      <span id="radiaTest">
        <n-gradient-text type="primary">radiaTest登录</n-gradient-text>
      </span>
    </div>
    <div>
      <n-form :rules="loginFormRules" :model="loginForm" ref="loginFormRef">
        <n-form-item style="--label-height: 6px" path="userName">
          <n-input
            round
            size="large"
            placeholder="请输入用户名"
            v-model:value="loginForm.userName"
            v-on:copy.prevent="handleFalse"
            v-on:cut.prevent="handleFalse"
            type="text"
          >
            <template #prefix>
              <n-icon size="20">
                <user />
              </n-icon>
            </template>
          </n-input>
        </n-form-item>
        <n-form-item style="--label-height: 6px; margin-top: -20px" path="passWord">
          <n-input
            round
            size="large"
            placeholder="请输入密码"
            type="password"
            v-model:value="loginForm.passWord"
            v-on:copy.prevent="handleFalse"
            v-on:cut.prevent="handleFalse"
          >
            <template #prefix>
              <n-icon size="20">
                <lock />
              </n-icon>
            </template>
          </n-input>
        </n-form-item>
      </n-form>
      <n-button type="primary" block round style="margin-top: 10px" @click="handleLoginByForm"
        >登录</n-button
      >
    </div>
  </n-modal>
</template>

<script>
import { defineComponent, getCurrentInstance, inject, watch } from 'vue';
import { BellOutlined } from '@vicons/antd';
import { modules } from './modules/index.js';
import { createAvatar } from '@/assets/utils/createImg';
import { storage } from '@/assets/utils/storageUtils';
import { User, Lock } from '@vicons/fa';
import { CaretDownOutline as CashIcon } from '@vicons/ionicons5';
export default defineComponent({
  components: {
    BellOutlined,
    User,
    Lock,
    CashIcon,
  },
  setup() {
    const { proxy } = getCurrentInstance();
    modules.getOrg();
    modules.getOrgList();
    const msgCount = inject('msgCount');
    const token = ref(storage.getValue('token'));
    const router = useRouter();
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
        deep: true,
      }
    );
    watch(
      () => router.currentRoute.value,
      () => {
        token.value = storage.getValue('token');
      },
      { immediate: true }
    );

    return {
      msgCount,
      createAvatar,
      token,
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

.profile-avatar {
  cursor: pointer;
  display: flex;
  align-items: center;
  background: rgba(204, 204, 204, 1);
}
.text-login {
  height: 100%;
  width: 40px;
  cursor: pointer;
  display: flex;
  align-items: center;
}
</style>
