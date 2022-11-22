<template>
  <div class="progressItem-container">
    <div class="line" v-for="(item, itemIndex) in dataList" :key="itemIndex">
      <div class="left" :class="{noLabel: !item.label}">{{item.label}}</div>
      <div class="right" :class="{noLabel: !item.label}" v-if="item.percentage">
        <div class="rh_top">
          <div class="rh_top_item">
            责任人：
            <span class="txtColor">{{item.responsible}}</span>
          </div>
          <div class="rh_top_item">
            协助人：
            <span class="txtColor">{{item.helper}}</span>
          </div>
          <div class="rh_top_item">
            开始时间：
            <span>{{item.startTime}}</span>
          </div>
          <div class="rh_top_item">
            截止时间：
            <span>{{item.endTime}}</span>
          </div>
        </div>
        <div class="rh_center">
          <n-progress
            type="line"
            :show-indicator="false"
            color="#002fa7"
            rail-color="#e2e6f3"
            :percentage="item.percentage"
          />
        </div>
        <div class="rh_bottom">
          <div>待办中</div>
          <div>进行中</div>
          <div>执行中</div>
          <div>已执行</div>
          <div>已完成</div>
        </div>
      </div>
      <div class="btn" v-else>
        <n-button strong round type="primary" @click="createTask">
          创建任务
        </n-button>
      </div>
    </div>
    <!-- <n-modal
      v-model:show="taskModal"
      preset="dialog"
      title="新建任务"
    >
      <n-form
        ref="taskRef"
        label-placement="top"
        :model="taskForm"
        :rules="taskRules"
      >
        <n-form-item label="责任人" path="responsible">
          <n-input
            v-model:value="taskForm.responsible"
            placeholder="请输入"
          />
        </n-form-item>
        <n-form-item label="协助人" path="helper">
          <n-input
            v-model:value="taskForm.helper"
            placeholder="请输入"
          />
        </n-form-item>
        <n-form-item label="开始时间" path="startTime">
          <n-date-picker v-model:value="taskForm.startTime" type="date" />
        </n-form-item>
        <n-form-item label="截止时间" path="endTime">
          <n-date-picker v-model:value="taskForm.endTime" type="date" />
        </n-form-item>
      </n-form>
      <template #action>
        <n-space style="width: 100%">
          <n-button type="error" ghost size="large" @click="closeTaskForm">
            取消
          </n-button>
          <n-button size="large" @click="submitTaskForm" type="primary" ghost>
            提交
          </n-button>
        </n-space>
      </template>
    </n-modal> -->
  </div>
</template>
<script>
const taskRules = {
  responsible: {
    trigger: ['blur', 'input'],
    message: '必填',
    required: true,
  },
  helper: {
    trigger: ['blur', 'input'],
    message: '必填',
    required: true,
  },
  startTime: {
    type: 'number',
    required: true,
    trigger: ['blur', 'change'],
    message: '必填',
  },
  endTime: {
    type: 'number',
    trigger: ['blur', 'change'],
    message: '必填',
    required: true,
  },
  
};
import { ref } from 'vue';
import router from '@/router';
export default {
  name: 'progressItem',
  components: {},
  props: {
    dataList: {
      type: Array,
      default: ()=>{
        return [];
      }
    }
  },
  methods: {
    createTask() {
      const { href } = router.resolve({
        path: '/home/tm/task',
        query: {
          type: 'caseManage'
        }
      });
      window.open(href, '_blank');
    },
    closeTaskForm() {},
    submitTaskForm() {
      this.taskRef.validate((errors) => {
        if (!errors) {
          //
        } else {
          window.$message?.error('填写信息有误,请检查!');
        }
      });
    },
  },
  setup() {
    return {
      taskModal: ref(false),
      taskRules,
      taskForm: ref({
        responsible: '',
        helper: '',
        startTime: null,
        endTime: null,
      }),
      taskRef: ref()
    };
  }
};
</script>
<style lang="less" scoped>
.progressItem-container{
  .line{
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding:15px 20px;
    border-top: 1px solid #eee;
    &:first-child{
      border-top: none;
    }
    .left{
      width: 15%;
      color: #000000;
      &.noLabel{
        width: 0%;
      }
    }
    .right{
      width: calc(85% - 40px);
      padding-right: 0px;
      &.noLabel{
        width: calc(100% - 40px);
      }
      .rh_top{
        display: flex;
        justify-content: flex-start;
        .rh_top_item{
          width:20%;
          color: #000000;
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
    .btn{
      .n-button{
        width: 150px;
      }
    }
  }
}

</style>
<style lang="less">
.progressItem-container{
  .rh_center{
    .n-progress .n-progress-graph .n-progress-graph-line .n-progress-graph-line-rail{
      height: 12px;
      border-radius: 10px;
    }
  }
}
</style>

