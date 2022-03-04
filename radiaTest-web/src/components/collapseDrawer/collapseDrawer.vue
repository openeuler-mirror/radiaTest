<template>
  <div class="drawer-body" ref="body">
    <div v-show="show" @click="outSideClick" class="drawer-dark"></div>
    <div class="collapse-container" ref="container">
      <div class="armrest" ref="armrest" @click="toggleDrawer">
        <n-tooltip trigger="hover">
          <template #trigger>
            <slot name="armrest">
              <n-icon
                size="40"
                color="#000"
                :depth="5"
                v-if="placement === 'right'"
              >
                <caret-back />
              </n-icon>
              <n-icon
                size="40"
                color="#000"
                :depth="5"
                v-else-if="placement === 'left'"
              >
                <caret-forward />
              </n-icon>
              <n-icon
                size="40"
                color="#000"
                :depth="5"
                v-else-if="placement === 'top'"
              >
                <caret-down-outline />
              </n-icon>
              <n-icon size="40" color="#000" :depth="5" v-else>
                <caret-up />
              </n-icon>
            </slot>
          </template>
          {{ show ? '收缩' : '展开' }}
        </n-tooltip>
      </div>
      <div class="content" ref="content">
        <slot name="content">
          <n-empty description="暂无内容"> </n-empty>
        </slot>
      </div>
    </div>
  </div>
</template>
<script>
import { CaretBack, CaretForward, CaretDownOutline, CaretUp } from '@vicons/ionicons5';
export default {
  components: { CaretBack, CaretForward, CaretDownOutline, CaretUp },
  props: {
    placement: {
      type: String,
      default: 'right'
    },
    contentWidth: {
      type: String,
      default: '200px'
    },
    outClickHide: {
      type: Boolean,
      default: false
    }
  },
  data() {
    return {
      show: false
    };
  },
  mounted() {
    if (this.placement === 'left' || this.placement === 'right') {
      // this.$refs.content.style.width = this.contentWidth;
      this.$refs.content.style.width = 0;
      this.$refs.content.style.height = '100%';
    } else {
      // this.$refs.content.style.height = this.contentWidth;
      this.$refs.content.style.height = 0;
      this.$refs.content.style.width = '100%';
    }
    this.getContainerPosition();
    this.getPosition();
  },
  methods: {
    outSideClick() {
      if (this.outClickHide) {
        this.close();
      }
    },
    toggleDrawer(e) {
      e.stopPropagation();
      if (!this.show) {
        this.open();
      } else {
        this.close();
      }
    },
    open() {
      if (this.placement === 'left' || this.placement === 'right') {
        this.$refs.content.style.width = this.contentWidth;
        this.$refs.container.style.transform = `translateX(${this.contentWidth})`;
        this.$refs.body.style.width = '100%';
      } else {
        this.$refs.content.style.height = this.contentWidth;
        this.$refs.container.style.transform = `translateY(${this.contentWidth})`;
        this.$refs.body.style.height = '100%';
      }
      this.$refs.armrest.style.transform = 'rotateZ(180deg)';
      this.show = true;
      setTimeout(() => {
        this.$refs.container.style.transition = 'transform 0.5s';
        this.$refs.container.style.transform = '';
      }, 10);
    },
    close() {
      this.show = false;
      if (this.placement === 'left' || this.placement === 'right') {
        this.$refs.container.style.transform = `translateX(${this.contentWidth})`;
        this.$refs.body.style.width = '';
      } else {
        this.$refs.container.style.transform = `translateY(${this.contentWidth})`;
        this.$refs.body.style.height = '';
      }
      this.$refs.armrest.style.transform = 'rotateZ(0deg)';
      setTimeout(() => {
        if (this.placement === 'left' || this.placement === 'right') {
          this.$refs.content.style.width = 0;
        } else {
          this.$refs.content.style.height = 0;
        }
        this.$refs.container.style.transform = 'translate(0)';
      }, 500);
    },
    getContainerPosition() {
      if (this.placement === 'left' || this.placement === 'right') {
        this.$refs.container.style.height = '100%';
        // this.$refs.container.style.transform = `translateX(${this.contentWidth})`;
        if (this.placement === 'left') {
          this.$refs.container.style.flexDirection = 'row-reverse';
        }
      } else {
        this.$refs.container.style.width = '100%';
        // this.$refs.container.style.transform = `translateY(${this.contentWidth})`;
        this.placement === 'top' ? this.$refs.container.style.flexDirection = 'column-reverse' : this.$refs.container.style.flexDirection = 'column';
      }
    },
    getPosition() {
      this.$refs.body.style[this.placement] = 0;
      console.log(this.$refs.armrest.style.clientWidth);
      if (this.placement === 'left' || this.placement === 'right') {
        this.$refs.body.style.height = '100%';
        this.$refs.body.style.top = 0;
        if (this.placement === 'left') {
          this.$refs.body.style.flexDirection = 'row-reverse';
        }
      } else {
        this.$refs.body.style.width = '100%';
        this.$refs.body.style.left = 0;
        this.placement === 'top' ? this.$refs.body.style.flexDirection = 'column-reverse' : this.$refs.body.style.flexDirection = 'column';
      }
    }
  }
};
</script>
<style scoped lang="less">
.drawer-body {
  position: fixed;
  z-index: 99999;
  display: flex;
  .collapse-container {
    display: flex;
    align-items: center;
    justify-content: center;
  }
  .drawer-dark {
    background: rgba(0, 0, 0, 0.7);
    width: 100%;
    height: 100%;
  }
  .content {
    overflow: hidden;
    background: #fff;
  }
  .armrest {
    cursor: pointer;
    background: #fff;
    transition: all 0.5s;
  }
}
</style>
