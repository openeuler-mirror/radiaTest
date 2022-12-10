<template>
  <div class="termNodes-container">
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
        <div class="chart" id="termAutomationRate-pie"></div>
      </div>
    </div>
    <div class="rightPart">
      <div class="part1">
        <div class="count count1">
          <div class="txt">commit合入统计</div>
          <div class="num">{{ commitsCount }}</div>
        </div>
        <div class="chart">
          <n-select v-model:value="commitSelectedTime" :options="timeOptions" />
          <div id="termCommitCounts-line"></div>
        </div>
      </div>
    </div>  
  </div>
  <div class="bottomPart">
    <n-tabs type="line" animated>
      <n-tab-pane name="baseline template" tab="基线模板">
        <baseline-template type="group"/>
      </n-tab-pane>
      <n-tab-pane name="codehub" tab="自动化脚本代码仓">
        <codehub type="group" />
      </n-tab-pane>
    </n-tabs>
  </div>
</template>
<script>
import { modules } from './modules/index';
import baselineTemplate from '../components/baselineTemplate';
import codehub from '../components/codehub';
import { Search } from '@vicons/ionicons5';
export default {
  components: { baselineTemplate, codehub },
  setup() {
    onMounted(() => {
      modules.initData();
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
      ...modules
    };
  }
};
</script>
<style lang="less" scoped>
.termNodes-container{
  display: flex;
  justify-content: space-between;
  flex-wrap: nowrap;
  .leftPart{
    width:40%;
    .part1{
      .chart{
        height: 100%;
        width: 50%;
      }
      .count{
        width: 25%;
      }
    }
  }
  .rightPart{
    width:calc(60% - 20px);
    .part1{
      .chart{
        height: 100%;
        width: 70%;
        .n-select{
          float: right;
          width: 20%;
          z-index: 1;
          margin-right: 20px;
        }
        #termCommitCounts-line{
          height: 100%;
        }
      }
      .count{
        width: 30%;
      }
    }
  }
  .part1{
    height: 200px;
    border:1px solid #eee;
    padding-top: 20px;
    padding-bottom: 20px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-radius: 4px;
    .count{
      text-align: center;
      height: auto;
      .txt{
        font-size: 14px;
        margin-bottom: 15px;
      }
      .num{
        font-family: Arial, Helvetica, sans-serif;
        font-size: 32px;
      }
    }
  }
}
.bottomPart{
  padding:20px;
  border:1px solid #eee;
  border-radius: 4px;
  margin-top:20px;
  .codehub{
    padding:20px;
    border:1px solid #eee;
    border-radius: 4px;
    margin-top:20px;
    .title{
      color: #000000;
      font-size: 16px;
      margin-bottom: 10px;
    }
    .search{
      overflow: hidden;
      margin-bottom: 15px;
      .n-button{
        float: left;
      }
      .n-input{
        float: right;
        width:200px;
        margin-right: 10px;
        margin-top:3px;
      }
      .n-icon.refreshIcon{
        float: right;
        margin-top:6px;
        cursor: pointer;
      }
    }
  }
  .baselineTemplate{
    display: flex;
    border:1px solid #eee;
    border-radius: 4px;
    margin-top:20px;
    justify-content: space-between;
    min-height: 600px;
    .baselineTemplate-left{
      width:20%;
      padding:20px;
      border-right: 1px solid #eee;
      .title{
        font-size: 16px;
        color:#000000;
      }
      .n-input{
        margin:10px 0;
      }
    }
    .baselineTemplate-right{
      width:80%;
      .top{
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
        .txts{
          display: flex;
          align-items: center;
          color:#666666;
          i{
            margin-right: 5px;
          }
        }
        .n-button{
          margin-left: 20px;
          height: 30px;
          padding-left: 24px;
          padding-right: 24px;
          border-radius: 24px;
        }
      }
    }
  }
}
</style>
<style lang="less">
.vue-kityminder{
  width: 100%;
  height: 100%;
  .vue-kityminder-toolbar-left{
    margin-top:20px;
    margin-left:20px;
    top:0 !important;
    left:0 !important;
    .vue-kityminder-btn{
      padding:8px 12px;
      font-size:14px;
    }
    .vue-kityminder-ml{
      margin-left:8px;
    }
    .vue-kityminder-control{
      padding: 8px;
    }
  }
}
</style>
