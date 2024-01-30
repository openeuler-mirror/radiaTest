<template>
  <div class="topPart">
    <div class="partMain part1">
      <div class="count">
        <div class="txt">测试套数量</div>
        <div class="num">{{ suitesCount }}</div>
      </div>
      <div class="count">
        <div class="txt">用例数</div>
        <div class="num">{{ casesCount }}</div>
      </div>
      <div class="chart" id="automationRate-pie"></div>
      <div class="chart" id="distribution-pie"></div>
    </div>
  </div>
</template>
<script>
import { modules } from './modules/index';
import { onMounted } from 'vue';
import { Close } from '@vicons/ionicons5';
export default {
  setup() {
    onMounted(() => {
      // modules.initData();
      nextTick(() => {
        modules.initData();
        setTimeout(() => {
          if (Number(sessionStorage.getItem('refresh')) === 1) {
            modules.dispatchRefreshEvent();
            sessionStorage.setItem('refresh', 0);
          }
        }, 500);
      });
    });
    return {
      Close,
      ...modules,
    };
  },
};
</script>
<style lang="less" scoped>
.topPart {
  width: 100%;
  display: flex;
  justify-content: space-between;
}
.partMain {
  height: 250px;
  width: 100%;
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid #eee;
  border-radius: 4px;
  padding-top: 20px;
  padding-bottom: 20px;
  margin-bottom: 20px;
  .count {
    width: 20%;
    text-align: center;
    height: auto;
    &.count1 {
      width: 10%;
    }
    .txt {
      font-size: 14px;
      margin-bottom: 15px;
    }
    .num {
      font-family: Arial, Helvetica, sans-serif;
      font-size: 32px;
    }
  }
  .chart {
    height: 100%;
    width: 23%;
  }
}
</style>
