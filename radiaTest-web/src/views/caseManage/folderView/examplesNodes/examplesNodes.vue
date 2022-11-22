<template>
  <div class="examplesNodes-container">
    <div class="topPart">
      <div class="partMain part1">
        <div class="count">
          <div class="txt">用例统计</div>
          <div class="num">{{ itemsCount }}</div>
        </div>
        <div class="chart" id="automationRate-pie"></div>
        <div class="chart" id="distribution-pie"></div>
      </div>
      <div class="partMain part2">
        <div class="count">
          <div class="txt">待评审commit</div>
          <div class="num">{{ itemsCount }}</div>
        </div>
        <div class="count">
          <div class="txt">待完成自动化用例</div>
          <div class="num">{{ itemsCount }}</div>
        </div>
      </div>
    </div>
    
    <div class="partMain">
      <div class="count count1">
        <div class="txt">月commit合入</div>
        <div class="num">{{ commitMonthCount }}</div>
      </div>
      <div class="count count1">
        <div class="txt">周commit合入</div>
        <div class="num">{{ commitWeekCount }}</div>
      </div>
      <div class="chart_1" id="commitCounts-bar"></div>
      <div class="chart_2">
        <n-select v-model:value="commitSelectedTime" :options="timeOptions" />
        <div id="commitCounts-line"></div>
      </div>
    </div>
    <div class="bottomPart">
      <div class="title">
        <div class="txt">自动化用例开发任务</div>
        <n-input type="text" size="small" v-model:value="keyword">
          <template #suffix>
            <n-icon color="666666" :component="Search" />
          </template>
        </n-input>
      </div>
      <div class="linesDetail">
        <progress-item 
          :data-list="autoExamplesList" 
          @createTask="createTask"
        />
      </div>
    </div>
  </div>
</template>
<script>
import { modules } from './modules/index';
import { ref, onMounted } from 'vue';
import { Search } from '@vicons/ionicons5';
import progressItem from '../components/progressItem.vue';
export default {
  components: { progressItem },
  setup() {
    onMounted(() => {
      modules.initData();
    });
    return {
      Search,
      commitSelectedTime: ref('week'),
      timeOptions: [
        { label: '近一周', value: 'week' },
        { label: '近半月', value: 'halfMonth' },
        { label: '近一月', value: 'month' },
      ],
      keyword: '', 
      ...modules
    };
  }
};
</script>
<style lang="less" scoped>
.examplesNodes-container{
  .topPart{
    width: 100%;
    display: flex;
    justify-content: space-between;
    .part1{
      width: calc(60% - 20px)
    }
    .part2{
      width: 40%;
      justify-content: space-around;
    }
  }
  .partMain{
    height: 250px;
    width: 100%;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border:1px solid #eee;
    border-radius: 4px;
    padding-top:20px;
    padding-bottom:20px;
    margin-bottom: 20px;
    .count{
      width:20%;
      text-align: center;
      height: auto;
      &.count1{
        width: 10%;
      }
      .txt{
        font-size: 14px;
        margin-bottom: 15px;
      }
      .num{
        font-family: Arial, Helvetica, sans-serif;
        font-size: 32px;
      }
    }
    .chart{
      height: 100%;
      width: 23%;
    }
    .chart_1{
      height: 100%;
      width: 30%;
    }
    .chart_2{
      height: 100%;
      width: 50%;
      .n-select{
        float: right;
        width: 20%;
        z-index: 1;
        margin-right: 20px;
      }
      #commitCounts-line{
        height: 100%;
      }
    }
  }
  .bottomPart{
    width: 100%;
    border:1px solid #eee;
    padding:0 10px;
    .title{
      display: flex;
      justify-content: space-between;
      padding: 0 20px;
      align-items: center;
      height: 40px;
      .txt{
        color: #000000;
        font-size: 14px;
      }
      .n-input{
        width:200px;
        margin-right: 10px;
      }
    }
    .linesDetail{
      height: auto;
      .line{
        display: flex;
        justify-content: space-between;
        align-items: center;
        padding:15px 20px;
        border-top: 1px solid #eee;
        .left{
          width: 15%;
        }
        .right{
          width: calc(85% - 80px);
          padding-right: 40px;
          .rh_top{
            display: flex;
            justify-content: flex-start;
            .rh_top_item{
              width:20%;
              .txtColor{
                color: #3da8f5;
                font-weight: bold;
              }
            }
          }
          .rh_center{
            margin:10px 0;
          }
          .rh_bottom{
            display: flex;
            justify-content: space-between;
            div{
              font-size: 12px;
              color:#666666;
            }
          }
        }
      }
    }
  }
}

</style>
<style lang="less">
.examplesNodes-container{
  .rh_center{
    .n-progress .n-progress-graph .n-progress-graph-line .n-progress-graph-line-rail{
      height: 12px;
      border-radius: 10px;
    }
  }
}
</style>

