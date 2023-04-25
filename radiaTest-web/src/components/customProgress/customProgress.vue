<template>
  <div class="custom-progress-bar">
    <!--有状态就显示状态的占比-->
    <div v-if="progress.total !== 0" class="bar-item-wrap">
      <n-popover trigger="hover">
        <template #trigger>
          <div class="bar-running" :style="{ width: runningWidth + '%' }">
            {{ progress.running }}
          </div>
        </template>
        <span>running {{ runningWidth.toFixed(2) }}%</span>
      </n-popover>
      <n-popover trigger="hover">
        <template #trigger>
          <div class="bar-check" :style="{ width: checkWidth + '%' }">
            {{ progress.success }}
          </div>
        </template>
        <span>passed {{ checkWidth.toFixed(2) }}%</span>
      </n-popover>
      <n-popover trigger="hover">
        <template #trigger>
          <div class="bar-fail" :style="{ width: failWidth + '%' }">
            {{ progress.failure }}
          </div>
        </template>
        <span>failed {{ failWidth.toFixed(2) }}%</span>
      </n-popover>
      <n-popover trigger="hover">
        <template #trigger>
          <div class="bar-skip" :style="{ width: blockWidth + '%' }">
            {{ progress.block }}
          </div>
        </template>
        <span>block {{ blockWidth.toFixed(2) }}%</span>
      </n-popover>
    </div>
    <!--无状态时显示0,bg是灰色-->
    <div v-else class="bar-item-wrap">
      <n-popover trigger="hover">
        <template #trigger>
          <div class="bar-no-data" style="width: 100%"></div>
        </template>
        <span>无数据 100%</span>
      </n-popover>
    </div>
    <span
      >{{ (progress?.success || 0) + (progress?.failure || 0) + (progress?.block || 0) + (progress?.running || 0) }}/{{
        progress?.total || 0
      }}</span
    >
  </div>
</template>

<script>
export default {
  data() {
    return {};
  },
  computed: {
    checkWidth() {
      return (this.progress.success / this.progress.total) * 100;
    },
    failWidth() {
      return (this.progress.failure / this.progress.total) * 100;
    },
    blockWidth() {
      return (this.progress.block / this.progress.total) * 100;
    },
    runningWidth() {
      return (this.progress.running / this.progress.total) * 100;
    }
  },
  props: {
    progress: {
      type: Object
    }
  },
  methods: {}
};
</script>

<style lang="scss">
.custom-progress-bar {
  display: flex;
  box-sizing: border-box;
  width: 100%;
  $h: 26px;

  .bar-item-wrap {
    text-align: center;
    color: white;
    border: 1px solid #f0f8ff;
    display: flex;
    flex-direction: row;
    justify-content: flex-start;
    align-items: center;
    margin: 2px;
    height: 19px;
    width: 90%;
    position: relative;
    border-radius: 13px;
    overflow: hidden;
    background: #e3e4ea;
    li {
      list-style: none;
    }
    .bar-running {
      overflow: hidden;
      background: #2080f0;
    }
    .bar-check {
      overflow: hidden;
      background: #18a058;
    }

    .bar-fail {
      overflow: hidden;
      background: #c20000;
    }

    .bar-skip {
      overflow: hidden;
      background: #f0f0f0;
    }

    .bar-no-data {
      overflow: hidden;
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
