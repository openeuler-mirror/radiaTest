<template>
  <n-grid :cols="64" style="align-items: center;height:100%">
    <n-gi :span="1" />
    <n-gi :span="9" class="myLogo">
      <n-space align="center">
        <div class="title" @click="router.push('/home')">
          <img src="/rediation.svg" style="height:50px" />
          <span id="radiaTest">
            <n-gradient-text type="primary">radiaTest</n-gradient-text>
          </span>
        </div>
      </n-space>
    </n-gi>
    <n-gi :span="38" class="myMenu">
      <header-menu v-if="showMenu" />
    </n-gi>
    <n-gi :span="4" class="menu">
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
    </n-gi>
    <n-gi :span="16" class="myProfile">
      <profile-menu />
    </n-gi>
  </n-grid>
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

<style scoped>
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
@media screen and (max-width: 1423px) {
  .menu {
    display: block;
  }
}
@media screen and (max-width: 1423px) {
  .myMenu {
    grid-column: none;
    position: absolute;
    left: 40%;
    top: 120px;
    width: 100%;
  }
}
@media screen and (max-width: 1423px) {
  .myLogo {
    grid-column: span 40 / span 40 !important;
  }
}
@media screen and (max-width: 1423px) {
  .myProfile {
    grid-column: span 20 / span 20 !important;
  }
}
@media screen and (max-width: 1129px) {
  .myLogo {
    grid-column: span 36 / span 36 !important;
  }
}
@media screen and (max-width: 1129px) {
  .myProfile {
    grid-column: span 24 / span 24 !important;
  }
}
@media screen and (max-width: 944px) {
  .myLogo {
    grid-column: span 32 / span 32 !important;
  }
}
@media screen and (max-width: 944px) {
  .myProfile {
    grid-column: span 28 / span 28 !important;
  }
}
@media screen and (max-width: 809px) {
  .myLogo {
    grid-column: span 56 / span 56 !important;
  }
}
@media screen and (max-width: 809px) {
  .myProfile {
    display: none;
  }
}
@media screen and (max-width: 525px) {
  .myLogo {
    grid-column: span 44 / span 44 !important;
  }
}
@media screen and (max-width: 525px) {
  .myMenu {
    left: 10%;
  }
}
</style>
