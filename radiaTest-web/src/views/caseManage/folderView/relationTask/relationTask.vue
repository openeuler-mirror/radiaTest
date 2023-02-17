<template>
  <div>
      <n-alert title="最新关联任务" type="info" round closable>
      <div class="alert-content">
        <n-grid :cols="24" :x-gap="24" :y-gap="18">
          <!--最新关联任务名称-->
          <n-gi :span="24">
            <div style="font-size: 16px; font-weight: 800">
              {{ task?.title }}
            </div>
          </n-gi>
          <!--任务责任人-->
          <n-gi :span="6">
            <span class="sub-title">责任人：</span>
            <!--用户信息组件，后续写成公共组件-->
            <userInfo :userInfo="task?.executor || {}" />
          </n-gi>
          <!--任务协助人-->
          <n-gi :span="6">
            <span class="sub-title"
              >协助人：{{ task?.originator?.user_name }}</span
            >
            <!--用户信息组件-->
          </n-gi>
          <!--任务开始时间-->
          <n-gi :span="6">
            开始时间：{{ formatTime(task?.start_time, 'yyyy-MM-dd') }}
          </n-gi>
          <!--任务结束时间-->
          <n-gi :span="6">
            结束时间： {{ formatTime(task?.deadline, 'yyyy-MM-dd') }}</n-gi
          >
          <n-gi :span="20">
            <n-steps status="process" size="small">
              <template v-for="item in status" :key="item.id">
                <n-step :title="item.name" :status="setStatus(item)" />
              </template>
            </n-steps>
          </n-gi>
          <n-gi :span="4">
            <!--未完成时需要disabled-->
            <n-button
              :disabled="task?.accomplish_time === null && !report.content"
              style="width: 100%"
              strong
              secondary
              round
              type="primary"
              @click="showReportModal = true"
            >
              查看报告
            </n-button>
          </n-gi>
        </n-grid>
      </div>
    </n-alert>
  </div>
</template>
<script>
import userInfo from '@/components/user/userInfo.vue';
import { modules } from './modules';
import { formatTime } from '@/assets/utils/dateFormatUtils';
export default {
  components:{
    userInfo
  },
  setup(){
    modules.getTask();
    return {
      ...modules,
      formatTime
    };
  }
};
</script>
