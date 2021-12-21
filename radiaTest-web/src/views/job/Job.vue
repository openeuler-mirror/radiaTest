<template>
  <n-card
    id="card"
    title="测试看板"
    size="huge"
    :segmented="{
      content: 'hard',
    }"
    header-style="
            font-size: 30px; 
            height: 80px; 
            font-family: 'v-sans';
            padding-top: 40px; 
            background-color: #FAFAFC;
        "
  >
    <div style="display: flex; flex-wrap: nowrap">
      <div
        style="width: calc(100% - 180px); display: block; margin-right: 36px"
      >
        <jobs-card type="execute" id="execute" />
        <jobs-card type="wait" id="wait" />
        <jobs-card type="finish" id="finish" />
      </div>
      <div style="width: 144px; display: block">
        <n-anchor
          affix
          :trigger-top="24"
          :top="88"
          style="z-index: 1; position: fixed"
          :bound="24"
          offset-target="#homeBody"
        >
          <n-anchor-link title="执行队列" href="#execute" />
          <n-anchor-link title="等待队列" href="#wait" />
          <n-anchor-link title="执行结果" href="#finish" />
        </n-anchor>
        <n-popover trigger="hover">
          <template #trigger>
            <div
              ref="createButton"
              style="
                position: fixed;
                height: 100px;
                bottom: 200px;
                color: rgba(206, 206, 206, 1);
              "
              @mouseenter="handleHover(createButton)"
              @mouseleave="handleLeave(createButton)"
              @click="createModalRef.show()"
            >
              <n-icon :size="80">
                <package />
              </n-icon>
            </div>
          </template>
          <span>快速执行单包任务</span>
        </n-popover>
        <modal-card
          :init-x="400"
          :init-y="200"
          ref="createModalRef"
          @validate="() => createFormRef.handlePropsButtonClick()"
          @submit="createFormRef.post()"
        >
          <template #form>
            <job-create-form
              ref="createFormRef"
              @valid="() => createModalRef.submitCreateForm()"
              @close="
                () => {
                  createModalRef.close();
                }
              "
            />
          </template>
        </modal-card>
      </div>
    </div>
    <logs-drawer ref="logsDrawer" />
    <template #action>
      <n-divider />
      <div
        style="
          text-align: center;
          color: grey;
          padding-top: 15px;
          padding-bottom: 0;
        "
      >
        {{ settings.name }} {{ settings.version }} · {{ settings.license }}
      </div>
    </template>
  </n-card>
</template>

<script>
import { provide, onMounted, onUnmounted, defineComponent } from 'vue';

import ModalCard from '@/components/CRUD/ModalCard.vue';
import Essential from '@/components/jobComponents';
import { Package } from '@vicons/tabler';
import LogsDrawer from '@/components/jobComponents/LogsDrawer.vue';

import { Socket } from '@/socket.js';
import settings from '@/assets/config/settings.js';
import job from './modules/job.js';

export default defineComponent({
  components: {
    ModalCard,
    ...Essential,
    Package,
    LogsDrawer,
  },
  setup() {
    const jobSocket = new Socket(`ws://${settings.serverPath}/job`);
    jobSocket.connect();

    provide('execute', job.execData);
    provide('wait', job.waitData);
    provide('finish', job.finishData);

    onMounted(() => {
      job.getData();

      jobSocket.listen('update', (res) =>
        job.devideData(job.changeTimeFormat(JSON.parse(res)))
      );
    });

    onUnmounted(() => {
      jobSocket.disconnect();
    });

    return {
      settings,
      ...job,
    };
  },
});
</script>

<style>
.n-progress-graph-line-indicator {
  line-height: 20px !important;
}
.progress {
  width: 200px;
}
</style>
