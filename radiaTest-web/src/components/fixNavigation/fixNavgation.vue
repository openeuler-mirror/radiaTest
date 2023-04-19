<template>
  <div class="fix-container">
    <vue3-draggable-resizable
      :draggable="true"
      :resizable="false"
      classNameDraggable="dragwrapbox"
      :h="dragboxHeight"
      :initW="60"
    >
      <div>
        <div ref="expandContainer" class="expandWrap">
          <n-tooltip trigger="hover" placement="right">
            <template #trigger>
              <p class="fix-item expand" @click="handleExpand">
                <n-icon size="40" color="#fff" :class="{ expandBack: expand }">
                  <add />
                </n-icon>
              </p>
            </template>
            {{ expand ? '隐藏' : '更多' }}
          </n-tooltip>
          <n-tooltip trigger="hover" placement="right">
            <template #trigger>
              <p class="fix-item expandable disabled">
                <n-icon size="40" color="#fff">
                  <ArrowSwap20Filled />
                </n-icon>
              </p>
            </template>
            语言切换
          </n-tooltip>
          <n-tooltip trigger="hover" placement="right">
            <template #trigger>
              <p class="fix-item expandable disabled">
                <n-icon size="40" color="#fff" v-if="lightTheme">
                  <MoonSharp />
                </n-icon>
                <n-icon size="40" color="#fff" v-else>
                  <Sunny />
                </n-icon>
              </p>
            </template>
            主题切换
          </n-tooltip>
        </div>
        <n-tooltip trigger="hover" placement="right">
          <template #trigger>
            <p class="fix-item" @click="backToTop">
              <n-icon size="40" color="#fff">
                <up-to-top />
              </n-icon>
            </p>
          </template>
          回到顶部
        </n-tooltip>
        <n-tooltip trigger="hover" placement="right">
          <template #trigger>
            <p class="fix-item" @click="backToBottom">
              <n-icon size="40" color="#fff">
                <down-to-bottom />
              </n-icon>
            </p>
          </template>
          回到底部
        </n-tooltip>
        <n-tooltip trigger="hover" placement="right">
          <template #trigger>
            <p class="fix-item" @click="jumpToGitee">
              <n-icon size="40" color="#fff" style="left: 2px; top: -2px">
                <svg
                  width="1rem"
                  height="1rem"
                  xmlns="http://www.w3.org/2000/svg"
                  name="zi_tmGitee"
                  viewBox="0 0 2000 2000"
                >
                  <path
                    d="M898 1992q183 0 344-69.5t283-191.5q122-122 191.5-283t69.5-344q0-183-69.5-344T1525 477q-122-122-283-191.5T898 216q-184 0-345 69.5T270 477Q148 599 78.5 760T9 1104q0 183 69.5 344T270 1731q122 122 283 191.5t345 69.5zm199-400H448q-17 0-30.5-14t-13.5-30V932q0-89 43.5-163.5T565 649q74-45 166-45h616q17 0 30.5 14t13.5 31v111q0 16-13.5 30t-30.5 14H731q-54 0-93.5 39.5T598 937v422q0 17 14 30.5t30 13.5h416q55 0 94.5-39.5t39.5-93.5v-22q0-17-14-30.5t-31-13.5H842q-17 0-30.5-14t-13.5-31v-111q0-16 13.5-30t30.5-14h505q17 0 30.5 14t13.5 30v250q0 121-86.5 207.5T1097 1592z"
                  />
                </svg>
              </n-icon>
            </p>
          </template>
          代码仓
        </n-tooltip>
      </div>
    </vue3-draggable-resizable>
  </div>
</template>
<script setup>
import { Add, Sunny, MoonSharp } from '@vicons/ionicons5';
import { UpToTop, DownToBottom } from '@vicons/carbon';
import { ArrowSwap20Filled } from '@vicons/fluent';
// import { changeTheme } from '@/assets/config/theme';
// import { darkTheme } from 'naive-ui';
import Vue3DraggableResizable from 'vue3-draggable-resizable';
import 'vue3-draggable-resizable/dist/Vue3DraggableResizable.css';

const route = useRoute();
const expand = ref(false);
const lightTheme = ref(true);
const dragboxHeight = ref(200);
const expandContainer = ref(null);

const backToTop = () => {
  if (route.name === 'resourcePool') {
    document.querySelector('#resourcePoolRight > div').scrollTop = 0;
  } else if (route.name === 'folderview') {
    document.querySelector('#folderviewRight > div').scrollTop = 0;
  } else {
    document.querySelector('#homeBody > div').scrollTop = 0;
  }
};
// const swapTheme = () => {
//   lightTheme.value = !lightTheme.value;
//   if (lightTheme.value) {
//     changeTheme(null);
//   } else {
//     changeTheme(darkTheme);
//   }
// };
const handleExpand = () => {
  expand.value = !expand.value;
  expandContainer.value.style.transition = 'all 1s';
  if (expand.value) {
    dragboxHeight.value = 300;
    expandContainer.value.style.height = '150px';
  } else {
    dragboxHeight.value = 200;
    expandContainer.value.style.height = '50px';
  }
};
const backToBottom = () => {
  if (route.name === 'resourcePool') {
    document.querySelector('#resourcePoolRight > div').scrollTop =
      document.querySelector('#resourcePoolRight > div').scrollHeight;
  } else if (route.name === 'folderview') {
    document.querySelector('#folderviewRight > div').scrollTop =
      document.querySelector('#folderviewRight > div').scrollHeight;
  } else {
    document.querySelector('#homeBody > div').scrollTop = document.querySelector('#homeBody > div').scrollHeight;
  }
};

const jumpToGitee = () => {
  window.open('https://gitee.com/openeuler/radiaTest');
};
</script>
<style lang="less" scoped>
.fix-container {
  position: fixed;
  right: 60px;
  bottom: 350px;
  z-index: 9999;
  cursor: move;

  :deep(.dragwrapbox) {
    border-color: transparent;
    border-style: dashed;
    display: flex;
    justify-content: center;
    align-items: top;

    &:hover {
      border-color: #000;
      border-style: dashed;
    }

    .expandWrap {
      overflow: hidden;
      width: 40px;
      height: 50px;
    }
  }

  .disabled {
    background: #ccc !important;
    cursor: not-allowed !important;
  }
  .fix-item:hover {
    background: rgba(0, 47, 167, 1);
  }
  .fix-item {
    cursor: pointer;
    background: rgba(204, 204, 204, 0.5);
    margin: 0;
    margin-bottom: 10px;
    display: flex;
    justify-content: center;
    align-items: center;
    border-radius: 50%;
    overflow: hidden;
    height: 40px;
    width: 40px;
    transition: all 1s;
    .expandBack {
      transform: rotateZ(45deg);
    }
  }
  .expand:hover {
    transform: rotate(180deg);
  }
}
</style>
