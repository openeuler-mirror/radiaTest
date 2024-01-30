<template>
  <div class="orgNodes-container">
    <div class="leftPart">
      <div class="part1">
        <div class="count">
          <div class="txt">测试套数量</div>
          <div class="num">{{ suitesCount }}</div>
        </div>
        <div class="count">
          <div class="txt">用例数量</div>
          <div class="num">{{ casesCount }}</div>
        </div>
        <div class="chart" id="orgAutomationRate-pie"></div>
      </div>
    </div>
  </div>
  <div class="bottomPart">
    <n-tabs type="line" animated>
      <n-tab-pane name="baseline template" tab="基线模板">
        <baseline-template type="org" :node-id="currentId" />
      </n-tab-pane>
      <n-tab-pane name="codehub" tab="自动化脚本代码仓">
        <codehub type="org" />
      </n-tab-pane>
    </n-tabs>
  </div>
</template>
<script>
import { modules } from './modules/index';
import baselineTemplate from '../components/baselineTemplate';
import codehub from '../components/codehub';
export default {
  components: {
    baselineTemplate,
    codehub,
  },
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
      ...modules,
    };
  },
};
</script>
<style lang="less" scoped>
.orgNodes-container {
  display: flex;
  justify-content: space-between;
  flex-wrap: nowrap;
  .leftPart {
    width: 100%;
    .part1 {
      .chart {
        height: 100%;
        width: 50%;
      }
      .count {
        width: 25%;
      }
    }
  }

  .part1 {
    height: 200px;
    border: 1px solid #eee;
    padding-top: 20px;
    padding-bottom: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-radius: 4px;
    .count {
      text-align: center;
      height: auto;
      .txt {
        font-size: 14px;
        margin-bottom: 15px;
      }
      .num {
        font-family: Arial, Helvetica, sans-serif;
        font-size: 32px;
      }
    }
  }
}
.bottomPart {
  padding: 20px;
  border: 1px solid #eee;
  border-radius: 4px;
  margin-top: 20px;
  .part {
    border: 1px solid #eee;
    padding-bottom: 20px;
    .top {
      height: 56px;
      width: calc(100% - 40px);
      display: flex;
      justify-content: space-between;
      align-items: center;
      color: #000000;
      font-size: 14px;
      border-bottom: 1px solid #eee;
      padding-left: 20px;
      padding-right: 20px;
      .txts {
        display: flex;
        align-items: center;
        margin-left: 20px;
        color: #666666;
        i {
          margin-right: 5px;
        }
      }
      .n-button {
        height: 30px;
        padding-left: 24px;
        padding-right: 24px;
        border-radius: 24px;
      }
    }
    .chart_3 {
      width: 100%;
      height: 360px;
    }
  }
}
</style>
