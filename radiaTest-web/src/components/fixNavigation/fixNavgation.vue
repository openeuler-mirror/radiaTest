<template>
  <div class="fix-container">
    <vue3-draggable-resizable :draggable="true" :resizable="false">
      <div style="overflow: hidden">
        <div ref="expandContainer">
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
    </vue3-draggable-resizable>
  </div>
</template>
<script>
import { Add, Sunny, MoonSharp } from '@vicons/ionicons5';
import { UpToTop, DownToBottom } from '@vicons/carbon';
import { ArrowSwap20Filled } from '@vicons/fluent';
import { changeTheme } from '@/assets/config/theme';
import { darkTheme } from 'naive-ui';
import Vue3DraggableResizable from 'vue3-draggable-resizable';
import 'vue3-draggable-resizable/dist/Vue3DraggableResizable.css';
export default {
  components: { Add, UpToTop, DownToBottom, ArrowSwap20Filled, Sunny, MoonSharp, Vue3DraggableResizable },
  data() {
    return {
      expand: false,
      lightTheme: true,
    };
  },
  mounted() {
    this.$refs.expandContainer.style.transform = `translateY(${2 * (document.querySelector('.expandable').clientHeight + 10)}px)`;
  },
  methods: {
    backToTop() {
      document.querySelector('#homeBody > div').scrollTop = 0;
    },
    swapTheme() {
      this.lightTheme = !this.lightTheme;
      if (this.lightTheme) {
        changeTheme(null);
      } else {
        changeTheme(darkTheme);
      }
    },
    handleExpand() {
      this.expand = !this.expand;
      const itemHeight = document.querySelector('.expandable').clientHeight;
      this.$refs.expandContainer.style.transition = 'transform 1s';
      if (this.expand) {
        this.$refs.expandContainer.style.transform = 'translateY(0)';
      } else {
        this.$refs.expandContainer.style.transform = `translateY(${2 * (itemHeight + 10)}px)`;
      }
    },
    backToBottom() {
      document.querySelector('#homeBody > div').scrollTop = document.querySelector('#homeBody > div').scrollHeight;
    }
  }
};
</script>
<style lang="less" scoped>
.fix-container {
  position: fixed;
  right: 50px;
  bottom: 350px;
  width: 50px;
  z-index: 9999;
  cursor: move;
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
    display: flex;
    margin: 0;
    margin-bottom: 10px;
    justify-content: center;
    align-items: center;
    border-radius: 50%;
    overflow: hidden;
    height: 50px;
    width: 50px;
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
