<template>
  <div class="wrapBox">
    <n-space align="center" class="logo">
      <div class="title" @click="router.push('/home')">
        <img src="/rediation.svg" style="height:50px" />
        <span id="radiaTest">
          <n-gradient-text type="primary">radiaTest</n-gradient-text>
        </span>
      </div>
    </n-space>
    <div class="myMenu">
      <header-menu v-if="showMenu" />
    </div>
    <div class="menu">
      <n-button
        style="top: 20%; height: 50%"
        @click="handleMenuClick"
        @blur="handleMenuBlur"
        v-if="showMenu"
      >
        <n-icon size="35">
          <menu-sharp />
        </n-icon>
      </n-button>
    </div>
    <div class="myProfile">
      <profile-menu />
    </div>
  </div>
</template>

<script>
import { defineComponent, inject } from 'vue';

import ProfileMenu from './profileMenu/ProfileMenu.vue';
import { useRouter } from 'vue-router';
import { MenuSharp } from '@vicons/ionicons5';

import HeaderMenu from './Menu.vue';

export default defineComponent({
  components: {
    HeaderMenu,
    ProfileMenu,
    MenuSharp,
  },
  setup(props, context) {
    const router = useRouter();
    const showMenu = inject('showMenu', true);

    return {
      router,
      showMenu,
      handleMenuClick() {
        context.emit('menuClick');
      },
      handleMenuBlur() {
        context.emit('menuBlur');
      },
    };
  },
});
</script>

<style scoped lang='less'>
.wrapBox{
  display:flex;
  justify-content:space-between;
  align-items: center;
  width: 100%;

  .logo{
    margin-left: 30px;
  }
}

.title {
  position: relative;
  display: contents;
  color: rgba(0, 47, 167, 1);
  display: flex;
  align-items: center;
}
.title #radiaTest {
  font-size: 40px;
  font-family: 'v-sans';
  width: 100%;
}
.title #radiaTest .n-gradient-text {
  font-weight: 800;
}
.myMenu {
  height: 100%;
  min-width: 850px;
}
.title:hover {
  cursor: pointer;
}
.st0 {
  fill: #002fa7;
}
.menu {
  display: none;
}

.myProfile{
  min-width: 375px;
}
</style>
