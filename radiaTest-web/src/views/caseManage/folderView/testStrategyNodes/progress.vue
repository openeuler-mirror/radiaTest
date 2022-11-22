<template>
  <div class="progress-container">
    <div class="topPart">
      <div class="partMain part1">
        <div class="count">
          <div class="txt">新增软件包/特性</div>
          <div class="num">{{ softwareCount }}</div>
        </div>
        <div class="count">
          <div class="txt">已完成测试覆盖</div>
          <div class="num">{{ testCount }}</div>
        </div>
        <div class="count">
          <div class="txt">预计完成时间</div>
          <div class="num">{{ finishTime }}</div>
        </div>
        <div class="chart" id="testPie"></div>
      </div>
      <div class="partMain part2">
        <div class="count">
          <div class="txt">新增用例</div>
          <div class="num">{{ exampleCount }}</div>
        </div>
        <div class="count">
          <div class="txt">新增自动化用例</div>
          <div class="num">{{ autoExampleCount }}</div>
        </div>
        <div class="chart" id="examplePie"></div>
      </div>
    </div>
    <div class="bottomPart">
      <!-- <div class="title">
        <div class="txt">自动化用例开发任务</div>
        <n-input type="text" size="small" v-model:value="keyword">
          <template #suffix>
            <n-icon color="666666" :component="Search" />
          </template>
        </n-input>
      </div> -->
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
      modules.progressInit();
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
.progress-container{
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
    border:1px solid #eee;
    padding:0 10px;
    .linesDetail{
      height: auto;
    }
  }
}

</style>
<style lang="less">
.progress-container{
  .rh_center{
    .n-progress .n-progress-graph .n-progress-graph-line .n-progress-graph-line-rail{
      height: 12px;
      border-radius: 10px;
    }
  }
}
</style>

