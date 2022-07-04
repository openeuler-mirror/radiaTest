<template>
  <div class="orgNodes-container">
    <div class="partMain">
      <div class="count">
        <div class="txt">用例统计</div>
        <div class="num">{{ itemsCount }}</div>
      </div>
      <div class="chart" id="automationRate-pie"></div>
      <div class="chart" id="contributionRatio-pie"></div>
      <div class="chart" id="distribution-pie"></div>
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
    <div class="part">
      <div class="top">
        <div style="display:flex">
          <div>测试项基线</div>
          <div class="txts">
            <n-icon size="16" color="#666666">
              <Cubes />
            </n-icon>
            树状视图
          </div>
        </div> 
        <n-button type="error">
          清空
        </n-button>
      </div>
      <div class="chart_3">
        <vue-kityminder
          style="height: 300px"
          ref="kityminder"
          theme="fresh-blue"
          template="structure"
          :value="val"
          :toolbar-status="toolbar"
        >
        </vue-kityminder>
      </div>
    </div>
  </div>
</template>
<script>
import { modules } from './modules/index';
import { ref, onMounted } from 'vue';
import { Cubes } from '@vicons/fa';
export default {
  components: { Cubes },
  setup() {
    onMounted(() => {
      modules.initData();
    });
    return {
      commitSelectedTime: ref('week'),
      timeOptions: [
        { label: '近一周', value: 'week' },
        { label: '近半月', value: 'halfMonth' },
        { label: '近一月', value: 'month' },
      ],
      val: {
        data: {
          id: 1,
          text: 'test'
        },
        children: [
          {
            data: {
              id: 2,
              text: 'test1'
            }
          },
          {
            data: {
              id: 3,
              text: 'test2'
            }
          }
        ]
      },
      toolbar: {
        appendSiblingNode: true,
        arrangeUp: false,
        arrangeDown: false,
        text: true,
        template: false,
        theme:false,
        hand: false,
        resetLayout: false,
        zoomIn: false,
        zoomOut:false
      },
      ...modules
    };
  }
};
</script>
<style lang="less" scoped>
.orgNodes-container{
  .partMain{
    height: 400px;
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
      width:18%;
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
  .part{
    border:1px solid #eee;
    padding-bottom:20px;
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
        margin-left: 20px;
        color:#666666;
        i{
          margin-right: 5px;
        }
      }
      .n-button{
        height: 30px;
        padding-left: 24px;
        padding-right: 24px;
        border-radius: 24px;
      }
    }
    .chart_3{
      width: 100%;
      height: 360px;
    }
  }
}

</style>
<style lang="less">
.orgNodes-container{
  .vue-kityminder{
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
}
</style>

