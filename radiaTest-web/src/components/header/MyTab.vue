<template>
  <n-popover
    style="margin-top: 0px; padding: 0"
    placement="bottom"
    trigger="hover"
    :show-arrow="false"
    ref="popover"
    @mouseenter="handleEnter"
    @mouseleave="handleLeave"
  >
    <template #trigger>
      <div
        :id="id"
        class="tab"
        ref="tab"
        @mouseenter="handleTabChoose"
        @mouseleave="handleTabLeave"
        @click="handleClick"
      >
        <div class="table-cell">
          <slot name="text"></slot>
          <n-icon class="arrow" ref="arrow" style="top: 3px; margin-left: 10px" v-show="hasArrow">
            <arrow-up />
          </n-icon>
        </div>
      </div>
    </template>
    <slot name="menu"></slot>
  </n-popover>
</template>

<script>
import { ref, onMounted, defineComponent } from 'vue';
import { KeyboardArrowUpSharp as ArrowUp } from '@vicons/material';

export default defineComponent({
  components: {
    ArrowUp
  },
  props: {
    hasArrow: {
      type: Boolean,
      default: true
    },
    url: {
      type: String,
      default: '/none'
    },
    disabled: Boolean,
    id: String
  },
  setup(props) {
    const popover = ref(null);
    const arrow = ref(null);
    const tab = ref(null);
    const isLeave = ref(true);

    onMounted(() => {
      if (props.disabled) {
        tab.value.style.color = 'grey';
      }
    });

    return {
      isLeave,
      popover,
      arrow,
      tab
    };
  },
  methods: {
    handleTabChoose() {
      if (!this.disabled) {
        this.$emit('choose');
        this.tab.style.color = 'rgba(0, 47, 167, 1)';
        this.tab.style.cursor = 'pointer';
        this.arrow.cssVars.transform = 'rotateX(180deg)';
      } else {
        this.tab.style.cursor = 'not-allowed';
      }
    },
    handleTabLeave() {
      if (this.isLeave && !this.disabled) {
        this.tab.style.color = 'black';
        this.tab.style.cursor = '';
        this.arrow.cssVars.transform = '';
        this.isLeave = true;
      }
    },
    handleEnter() {
      this.isLeave = false;
      this.tab.style.color = 'rgba(0, 47, 167, 1)';
    },
    handleLeave() {
      this.isLeave = true;
      this.tab.style.color = 'black';
      this.tab.style.cursor = '';
      this.arrow.cssVars.transform = '';
    },
    handleClick() {
      this.$emit('click');
    }
  }
});
</script>

<style scoped>
.table-cell {
  display: table-cell;
  vertical-align: bottom;
}
.tab {
  display: table;
  position: relative;
  margin-left: 10px;
  margin-right: 10px;
  text-align: center;
  font-size: 14px;
  font-family: v-sans;
  float: left;
}

.arrow {
  transition: all 0.4s ease-in-out;
}
</style>
