<template>
  <div v-if="showDetail">
    <n-alert title="最新关联任务" type="info" round closable>
      <div class="alert-content">
        <n-grid :cols="24" :x-gap="24" :y-gap="18">
          <!--最新关联任务名称-->
          <n-gi :span="24">
            <div style="font-size: 16px; font-weight: 800">
              openEuler 20.03-LTS-SP1 update 211224 oe_test_nginx_lvs_base
            </div>
          </n-gi>
          <!--任务责任人-->
          <n-gi :span="6">
            <span class="sub-title">责任人：</span>
            <!--用户信息组件，后续写成公共组件-->
            <n-popover
              placement="right-start"
              trigger="hover"
              :show-arrow="false"
              raw
            >
              <template #trigger>
                <span class="sub-content user">张以正</span>
              </template>
              <n-card>
                <div
                  style="
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                  "
                >
                  <n-avatar
                    round
                    :size="96"
                    src="https://07akioni.oss-cn-beijing.aliyuncs.com/07akioni.jpeg"
                  />
                  <div style="padding-top: 20px">
                    <p style="text-align: center">
                      <span>张以正</span>
                    </p>
                    <p style="padding-top: 20px">
                      <span>手机：</span>
                      <span>13430919587</span>
                    </p>
                    <p>
                      <span>邮箱：</span>
                      <span>ethanzhang55@outlook.com</span>
                    </p>
                  </div>
                </div>
              </n-card>
            </n-popover>
          </n-gi>
          <!--任务协助人-->
          <n-gi :span="6">
            <span class="sub-title">协助人：</span>
            <!--用户信息组件-->
          </n-gi>
          <!--任务开始时间-->
          <n-gi :span="6"> 开始时间：2021-12-29 00:00:00 </n-gi>
          <!--任务结束时间-->
          <n-gi :span="6"> 结束时间： </n-gi>
          <n-gi :span="20">
            <n-steps :current="2" status="process" size="small">
              <n-step title="待办的" />
              <n-step title="进行中" />
              <n-step title="执行中" />
              <n-step title="已执行" />
              <n-step title="已完成" />
            </n-steps>
          </n-gi>
          <n-gi :span="4">
            <!--未完成时需要disabled-->
            <n-button style="width: 100%" strong secondary round type="primary">
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
          margin-bottom: 10px;
        "
      >
        <n-tabs type="line" @update:value="tabChange" :value="activeTab">
          <n-tab name="details">详情</n-tab>
          <n-tab name="historicalExec">历史执行</n-tab>
          <n-tab name="auto" :disabled="!caseInfo.code">自动化脚本</n-tab>
          <n-tab name="historicalVersion" disabled>历史版本</n-tab>
        </n-tabs>
        <!--存在未完成关联任务时disabled-->
        <n-button strong secondary round type="primary">创建关联任务</n-button>
      </div>
      <n-card size="large">
        <template v-if="activeTab === 'details'">
          <collapse-list :list="detailsList" />
        </template>
        <template v-else-if="activeTab === 'historicalExec'">
          <historical-exec :case="caseInfo" />
        </template>
        <template v-else-if="activeTab === 'auto'">
          <auto-script :code="caseInfo.code" />
        </template>
        <template v-else>{{ activeTab }}</template>
      </n-card>
    </div>
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
import { ref, provide } from 'vue';
export default {
  components: {
    collapseList,
    historicalExec,
    autoScript,
  },
  mounted() {
    if (this.$route.params.taskid === 'development') {
      this.showDetail = false;
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
      showDetail,
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
