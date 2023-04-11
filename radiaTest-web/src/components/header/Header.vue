<template>
  <div class="wrapBox">
    <n-space align="center" class="logo">
      <div class="title" @click="clickLogo">
        <img src="/rediation.svg" style="height: 30px" />
        <span id="radiaTest">
          <n-gradient-text type="primary">radiaTest</n-gradient-text>
        </span>
      </div>
    </n-space>
    <div class="myMenu" v-if="showFunctionMenu">
      <header-menu />
    </div>
    <div class="myMenu" v-else>
      <HomeMenu></HomeMenu>
    </div>
    <div class="myProfile">
      <profile-menu />
    </div>
  </div>
</template>

<script setup>
import ProfileMenu from './profileMenu/ProfileMenu.vue';
import { useRouter } from 'vue-router';
import HeaderMenu from './Menu.vue';
import { showFunctionMenu } from '@/assets/config/menu.js';

const router = useRouter();

const clickLogo = () => {
  router.push('/home');
};
</script>

<style scoped lang="less">
.wrapBox {
  display: flex;
  justify-content: space-between;
  align-items: center;
  width: 100%;

  .logo {
    margin-left: 30px;
  }
}

.title {
  position: relative;
  display: contents;
  color: rgba(0, 47, 167, 1);
  display: flex;
  align-items: center;
  margin-right: 20px;
}
.title #radiaTest {
  font-size: 30px;
  font-family: 'v-sans';
  width: 100%;
}
.title #radiaTest .n-gradient-text {
  font-weight: 800;
}
.myMenu {
  min-width: 850px;
  display: flex;
}
.title:hover {
  cursor: pointer;
}
.st0 {
  fill: #002fa7;
}

.myProfile {
  min-width: 375px;
}
</style>
