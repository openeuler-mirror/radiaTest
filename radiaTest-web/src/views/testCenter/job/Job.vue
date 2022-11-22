<template>
  <div style="display: flex; padding-top: 20px;">
    <div style="width: 100%">
      <jobs-card type="execute" id="execute" ref="executeRef" />
      <jobs-card type="wait" id="wait" ref="waitRef" />
      <jobs-card type="finish" id="finish" ref="finishRef" />
    </div>
    <div
      style="
        width: 144px;
        display: flex;
        flex-direction: column;
        align-items: center;
        flex-shrink: 0;
      "
    >
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
              bottom: 300px;
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
</template>

<script>
import { ref, provide, onMounted, onUnmounted, defineComponent } from 'vue';

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
    const jobSocket = new Socket(`${settings.websocketProtocol}://${settings.serverPath}/job`);
    jobSocket.connect();
    const finishRef = ref();
    const waitRef = ref();
    const executeRef = ref();

    provide('execute', job.execData);
    provide('wait', job.waitData);
    provide('finish', job.finishData);

    onMounted(() => {

      jobSocket.listen('update', () => {
        executeRef.value.getData();
        waitRef.value.getData();
        finishRef.value.getData();
      }
      );
    });

    onUnmounted(() => {
      jobSocket.disconnect();
    });

    return {
      settings,
      ...job,
      finishRef,
      waitRef,
      executeRef
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
