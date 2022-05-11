<template>
  <div>
    <div style="display:flex;align-items:center">
      <template v-for="(item, index) in list" :key="item.key">
        <input
          type="radio"
          :checked="item.success"
          @click="handleChange(index)"
          style="zoom:200%"
        />
        <span class="step-label">{{ item.text }}</span>
        <n-divider v-if="index !== list.length - 1" />
      </template>
      <n-tooltip v-if="!done" :show-arrow="false" trigger="hover">
        <template #trigger>
          <n-divider
            dashed
            @mouseenter="changeHover(true)"
            @mouseleave="changeHover(false)"
          >
            <n-icon :color="hover ? '#4098fc' : ''" @click="addStep">
              <ArrowCircleRight24Regular />
            </n-icon>
          </n-divider>
        </template>
        {{ addTip }}
      </n-tooltip>
      <n-divider v-else />
      <input @click="doneEvent" :title="doneTip" type="radio" style="zoom:200%" />
      <span class="step-label">release</span>
    </div>
  </div>
</template>
<script>
import { ArrowCircleRight24Regular } from '@vicons/fluent';
export default {
  props: {
    list: Array,
    addTip: {
      type: String,
      default: '下一轮迭代',
    },
    doneTip: {
      type: String,
      default: '点击后结束迭代',
    },
    done: {
      type: Boolean,
      default: false,
    },
  },
  components: {
    ArrowCircleRight24Regular,
  },
  data() {
    return {
      hover: false,
    };
  },
  methods: {
    addStep(){
      this.$emit('add');
    },
    doneEvent(){
      this.$emit('done');
    },
    changeHover(show) {
      this.$nextTick(() => {
        this.hover = show;
      });
    },
    handleChange(index) {
      this.$emit('stepClick', index);
    },
  },
};
</script>
<style lang="less" scoped>
.step-label{
  width: 150px;
  display: inline-block;
  word-break: break-all;
}
</style>
