<template>
  <div class="collapse-container" ref="container">
    <div class="armrest" ref="armrest" @click="toggleDrawer" v-show="!show">
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
      <n-drawer
        display-directive="if"
        v-model:show="show"
        :width="contentWidth"
        :height="contentWidth"
        :mask-closable="outClickHide"
        :placement="placement"
      >
        <n-drawer-content>
          <slot name="content">
            <n-empty description="暂无内容"> </n-empty>
          </slot>
        </n-drawer-content>
      </n-drawer>
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
      default: true
    }
  },
  data() {
    return {
      show: false
    };
  },
  mounted() {
    if (this.placement === 'left' || this.placement === 'right') {
      this.$refs.armrest.style.top = '50%';
      this.$refs.armrest.style.transform = 'translateY(-50%)';
    } else {
      this.$refs.armrest.style.left = '50%';
      this.$refs.armrest.style.transform = 'translateX(-50%)';
    }
    this.$refs.armrest.style[this.placement] = 0;
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
      this.show = true;
    },
    close() {
      this.show = false;
    }
  }
};
</script>
<style scoped lang="less">
.armrest {
  cursor: pointer;
  position: fixed;
  z-index: 9999;
}
</style>
