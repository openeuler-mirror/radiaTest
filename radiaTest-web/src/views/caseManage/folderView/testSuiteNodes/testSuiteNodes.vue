<template>
  <div class="testSuiteNodes-container">
    <div class="top_tip" v-if="showProgress">
      <div class="title">
        <n-icon size="20" class="closeIcon" :component="Close" @click="showProgress = false" />
        <span class="txt">{{ title }}</span> 
      </div>
      <div class="tip_progress">
        <progress-item 
          :data-list="testSuiteProgress"
        />
        <n-button strong round type="primary" @click="openReport">
          查看报告
        </n-button>
      </div>
    </div>
    <div class="testSuiteNodes-tabs">
      <div class="tabsTip">
        <n-button strong round type="success" @click="createVersionTask">
          创建用例开发任务
        </n-button>
      </div>
      <n-tabs type="line" animated>
        <n-tab-pane name="document" tab="软件包/特性文档">
          <Document />
        </n-tab-pane>
      </n-tabs>
    </div>
  </div>
</template>
<script>
import { modules } from './modules/index';
import { onMounted, ref } from 'vue';
import { Close } from '@vicons/ionicons5';
import progressItem from '../components/progressItem.vue';
import Document from './document.vue';
export default {
  components: { 
    progressItem,
    Document 
  },
  setup() {
    onMounted(() => {
      modules.initData();
    });
    return {
      Close,
      title: 'abrt测试套用例开发任务',
      showProgress: ref(true),
      ...modules
    };
  }
};
</script>
<style lang="less" scoped>
.testSuiteNodes-container{
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
 .testSuiteNodes-tabs{
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
.testSuiteNodes-container{
 .tip_progress{
  .progressItem-container{
    .line{
      border: none;
    }
  }
 }
}
</style>

