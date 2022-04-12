<template>
  <div v-if="showDetail">
    <n-alert title="最新关联任务" type="info" round closable>
      <div class="alert-content">
        <n-grid :cols="24" :x-gap="24" :y-gap="18">
          <!--最新关联任务名称-->
          <n-gi :span="24">
            <div style="font-size: 16px; font-weight: 800">
              {{ task.title }}
            </div>
          </n-gi>
          <!--任务责任人-->
          <n-gi :span="6">
            <span class="sub-title">责任人：</span>
            <!--用户信息组件，后续写成公共组件-->
            <userInfo :userInfo="task.executor || {}" />
            <!-- <n-popover
              placement="right-start"
              trigger="hover"
              :show-arrow="false"
              raw
            >
              <template #trigger>
                <span class="sub-content user">{{
                  task.executor?.gitee_name
                }}</span>
              </template>
              <n-card>
                <div
                  style="
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                  "
                >
                  <n-avatar round :size="96" :src="task.executor?.avatar_url" />
                  <div style="padding-top: 20px">
                    <p style="text-align: center">
                      <span>{{ task.executor?.gitee_name }}</span>
                    </p>
                    <p style="padding-top: 20px">
                      <span>手机：</span>
                      <span>{{ task.executor?.phone }}</span>
                    </p>
                    <p>
                      <span>邮箱：</span>
                      <span>{{ task.executor?.cla_email }}</span>
                    </p>
                  </div>
                </div>
              </n-card>
            </n-popover> -->
          </n-gi>
          <!--任务协助人-->
          <n-gi :span="6">
            <span class="sub-title"
              >协助人：{{ task.originator?.gitee_name }}</span
            >
            <!--用户信息组件-->
          </n-gi>
          <!--任务开始时间-->
          <n-gi :span="6">
            开始时间：{{ formatTime(task.start_time, 'yyyy-MM-dd') }}
          </n-gi>
          <!--任务结束时间-->
          <n-gi :span="6">
            结束时间： {{ formatTime(task.deadline, 'yyyy-MM-dd') }}</n-gi
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
              :disabled="task.accomplish_time === null && !report.content"
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
    <div class="details-container">
      <div
        style="
          display: flex;
          justify-content: space-between;
          margin: 10px 0;
        "
      >
        <n-tabs type="line" @update:value="tabChange" :value="activeTab">
          <n-tab name="details">详情</n-tab>
          <n-tab name="historicalExec">历史执行</n-tab>
          <n-tab name="auto" :disabled="!caseInfo.code">自动化脚本</n-tab>
          <n-tab name="historicalVersion" >历史版本</n-tab>
        </n-tabs>
        <!--存在未完成关联任务时disabled-->
        <n-button
          strong
          secondary
          round
          type="primary"
          :disabled="task.accomplish_time === null"
          @click="showCreateForm"
          >创建关联任务</n-button
        >
      </div>
      <n-card size="large">
        <n-spin stroke="rgba(0, 47, 167, 1)" :show="loading">
          <template v-if="activeTab === 'details'">
            <collapse-list :list="detailsList" @edit="edit" />
          </template>
          <template v-else-if="activeTab === 'historicalExec'">
            <historical-exec :case="caseInfo" />
          </template>
          <template v-else-if="activeTab === 'auto'">
            <auto-script :code="caseInfo.code" />
          </template>
          <template v-else>
            <historical-version/>
          </template>
        </n-spin>
      </n-card>
    </div>
    <create-drawer ref="createForm" @submit="createRelationTask" />
    <caseModifyForm ref="modifyModal" :formValue="editInfoValue" @submit="editSubmit" />
    <n-modal
      v-model:show="showReportModal"
      preset="dialog"
      :show-icon="false"
      title="Dialog"
      class="previewWindow"
      :style="{ width: previewWidth + 'px', height: previewHeight + 'px' }"
    >
      <template #header>
        <h3>{{ report.name }}</h3>
      </template>
      <div
        class="previewContent"
        :style="{ height: previewHeight - 100 + 'px' }"
      >
        <v-md-editor
          v-model="report.content"
          :left-toolbar="tools"
          :right-toolbar="rightTools"
          :include-level="[1, 4]"
          :toolbar="toolbar"
        ></v-md-editor>
      </div>
    </n-modal>
  </div>
  <div
    v-else
    style="
      height: 100%;
      width: 100%;
      display: flex;
      justify-content: center;
      align-items: center;
    "
  >
    <n-empty description="开发中..."> </n-empty>
  </div>
</template>
<script>
import { modules } from './modules';
import collapseList from '@/components/collapseList/collapseList.vue';
import historicalExec from './tabview/historicalExec.vue';
import autoScript from './tabview/autoScript.vue';
import createDrawer from '@/components/task/createDrawer.vue';
import historicalVersion from './tabview/historicalVersion.vue';

import { ref, provide } from 'vue';
import { formatTime } from '@/assets/utils/dateFormatUtils';
import caseModifyForm from '@/components/testcaseComponents/caseModifyForm.vue';
import {
  previewWidth,
  previewHeight,
} from '@/views/taskManage/task/modules/mdFile';
import userInfo from '@/components/user/userInfo.vue';
export default {
  components: {
    collapseList,
    historicalExec,
    autoScript,
    createDrawer,
    userInfo,
    historicalVersion,
    caseModifyForm
  },
  mounted() {
    if (this.$route.params.taskid === 'development') {
      this.showDetail = false;
      sessionStorage.setItem('refresh', 0);
    } else {
      this.$nextTick(() => {
        this.getDetail(this.$route.params.taskid);
        setTimeout(() => {
          if (Number(sessionStorage.getItem('refresh')) === 1) {
            window.dispatchEvent(
              new CustomEvent('refreshEvent', {
                detail: { baselineId: this.$route.params.taskid },
              })
            );
            sessionStorage.setItem('refresh', 0);
          }
        }, 500);
      });
    }
  },
  setup() {
    const showDetail = ref(true);
    provide('caseInfo', modules.caseInfo);
    return {
      previewWidth,
      previewHeight,
      showDetail,
      formatTime,
      ...modules,
    };
  },
};
</script>
<style lang="less" scoped>
.user {
  color: #4ca8ff;
  font-weight: 600;
}
.user:hover {
  cursor: pointer;
}
.alert-content {
  display: flex;
  justify-content: space-between;
}
.details-container {
  height: 100%;
  overflow-y: auto;
}
</style>
