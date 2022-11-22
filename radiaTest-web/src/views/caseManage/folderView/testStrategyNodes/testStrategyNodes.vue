<template>
  <div class="testStrategyNodes-container">
    <div class="top_tip">
      <div class="title">
        <n-icon size="20" class="closeIcon" :component="Close" />
        <span class="txt">{{ title }}</span> 
      </div>
      <div class="tip_progress">
        <progress-item 
          :data-list="testStrategyProgress"
        />
        <n-button strong round type="primary" @click="openReport">
          查看报告
        </n-button>
      </div>
    </div>
    <div class="testStrategyNodes-tabs">
      <div class="tabsTip">
        <div class="baseline">
          应用基线：<span>{{ baseline }}</span>
        </div>
        <n-button strong round type="success" @click="createVersionTask">
          创建版本任务
        </n-button>
      </div>
      <n-tabs type="line" animated>
        <n-tab-pane name="document" tab="版本测试策略文档">
          <Document />
        </n-tab-pane>
        <n-tab-pane name="progress" tab="新增软件包/特性用例开发进度跟踪">
          <Progress />
        </n-tab-pane>
      </n-tabs>
    </div>
  </div>
</template>
<script>
import { modules } from './modules/index';
import { onMounted } from 'vue';
import { Close } from '@vicons/ionicons5';
import progressItem from '../components/progressItem.vue';
import Progress from './progress.vue';
import Document from './document.vue';
export default {
  components: { 
    progressItem,
    Progress,
    Document 
  },
  setup() {
    onMounted(() => {
      modules.initData();
    });
    return {
      Close,
      title: 'openEuler 22.03 LTS 版本任务',
      ...modules
    };
  }
};
</script>
<style lang="less" scoped>
.testStrategyNodes-container{
 .top_tip{
  height: auto;
  border-radius: 5px;
  background-color: #d2daf5;
  position: relative;
  padding: 12px 12px 0 12px;
  margin-bottom: 20px;
  .title{
    display: flex;
    align-items: center;
    .closeIcon{
      color:#666666;
      cursor: pointer;
    }
    .txt{
      font-size: 16px;
      color:#002fa7;
      font-weight: bold;
      margin-left: 10px;
    }
  }
 }
 .testStrategyNodes-tabs{
  position: relative;
  .tabsTip{
    position: absolute;
    right: 0;
    display: flex;
    align-items: center;
    z-index: 10;
    .baseline{
      margin-right: 50px;
      font-size: 14px;
      span{
        color:#3da8f5;
        font-weight: bold;
      }
    }
  }
  .n-tabs .n-tab-pane{
    padding-top: 0px;
  }
 }
 .tip_progress{
  display: flex;
  justify-content: space-around;
  align-items: center;
  .progressItem-container{
    width: calc(100% - 140px);
  }
  .n-button{
    width: 100px
  }
 }
}

</style>
<style lang="less">
.testStrategyNodes-container{
 .tip_progress{
  .progressItem-container{
    .line{
      border: none;
    }
  }
 }
}
</style>

