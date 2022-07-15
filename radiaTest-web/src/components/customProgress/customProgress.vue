<template>
  <div class="custom-progress-bar">
    <!--有状态就显示状态的占比-->
    <div v-if="progress.total !== 0" class="bar-item-wrap">
      <n-popover trigger="hover">
        <template #trigger>  
          <div class="bar-check" :style="{width:checkWidth + '%'}"></div>
        </template>
        <span>已通过 {{ checkWidth.toFixed(2) }}%</span>
      </n-popover>
      <n-popover trigger="hover">
        <template #trigger>  
          <div class="bar-fail" :style="{width:failWidth + '%'}"></div>
        </template>
        <span>未通过 {{ failWidth.toFixed(2) }}%</span>
      </n-popover>
      <n-popover trigger="hover">
        <template #trigger>  
          <div class="bar-apply" :style="{width:applyWidth + '%'}"></div>
        </template>
        <span>待校验 {{ applyWidth.toFixed(2) }}%</span>
      </n-popover>
    </div>
    <!--无状态时显示0,bg是灰色-->
    <div v-else class="bar-item-wrap">
        <n-popover trigger="hover">
          <template #trigger>  
            <div class="bar-no-data" style="width: 100%;"></div>
          </template>
          <span>无数据 100%</span>
        </n-popover>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {};
  },
  computed: {
    checkWidth() {
      return (this.progress.checkNum / this.progress.total) * 100;
    },
    failWidth() {
      return (this.progress.failNum / this.progress.total) * 100;
    },
    applyWidth() {
      return (this.progress.applyNum / this.progress.total) * 100;
    }
  },
  props: {
    progress: {
      type: Object,
    }
  },
  methods: {
  },

};
</script>

<style lang="scss">
.custom-progress-bar {
  box-sizing: border-box;
  width: 100%;
  $h: 26px;

  .bar-item-wrap {
    border: 1px solid #F0F8FF;
    display: flex;
    flex-direction: row;
    justify-content: flex-start;
    align-items: center;
    margin: 2px;
    height: 19px;
    position: relative;
    border-radius: 13px;
    overflow: hidden;
    background: #e3e4ea;
    width: 283px;
    right: 30px;
    li {
        list-style: none;
    }

    .bar-check {
      height: 100%;
      background: #2080F0;
    }

    .bar-fail {
      height: 100%;
      background: #99c1e9;
    }

    .bar-apply {
      height: 100%;
      background: #F0F0F0;
    }

    .bar-no-data {
      height: 100%;
      background: #e3e4ea;
    }
  }

  .percentage-num {
    position: absolute;
    top: 50%;
    right: 20px;
    transform: translateY(-50%);
    font-size: 9px;
    color: white;
    height: $h;
    line-height: $h;
    text-align: center;
  }
}
</style>
