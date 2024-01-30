<template>
  <div class="casesetNodes-container">
    <div class="topPart">
      <div class="partMain part1">
        <div class="count">
          <div class="txt">测试套数量</div>
          <div class="num">{{ suitesCount }}</div>
        </div>
        <div class="count">
          <div class="txt">用例数量</div>
          <div class="num">{{ casesCount }}</div>
        </div>
        <div class="chart" id="automationRate-pie"></div>
        <div class="chart" id="distribution-pie"></div>
      </div>
    </div>
    <!-- <div class="partMain">
      <div class="count count1">
        <div class="txt">commit合入</div>
        <div class="num">{{ commitsCount }}</div>
      </div>
      <div class="chart_1" id="commitCounts-bar"></div>
      <div class="chart_2">
        <n-select v-model:value="commitSelectedTime" :options="timeOptions" />
        <div id="commitCounts-line"></div>
      </div>
    </div> -->
  </div>
</template>
<script>
import { modules } from './modules/index';
import { Search } from '@vicons/ionicons5';
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
      Search,
      ...modules,
    };
  },
};
</script>
<style lang="less" scoped>
.casesetNodes-container {
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
        width: 20%;
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
    .chart_1 {
      height: 100%;
      width: 30%;
    }
    .chart_2 {
      height: 100%;
      width: 50%;
      .n-select {
        float: right;
        width: 20%;
        z-index: 1;
        margin-right: 20px;
      }
      #commitCounts-line {
        height: 100%;
      }
    }
  }
}
</style>
<style lang="less">
.casesetNodes-container {
  .rh_center {
    .n-progress .n-progress-graph .n-progress-graph-line .n-progress-graph-line-rail {
      height: 12px;
      border-radius: 10px;
    }
  }
}
</style>
