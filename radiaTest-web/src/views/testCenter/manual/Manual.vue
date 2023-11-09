<template>
  <div class="manualContainer">
    <div style="width: 100%">
      <manual-list type="execute" id="execute" ref="executeRef" />
      <manual-list type="finish" id="finish" ref="finishRef" />
    </div>
    <div class="anchorWrap">
      <n-anchor
        affix
        :trigger-top="24"
        :top="88"
        class="anchor"
        :bound="24"
        offset-target="#homeBody"
      >
        <n-anchor-link title="执行队列" href="#execute" />
        <n-anchor-link title="执行结果" href="#finish" />
      </n-anchor>
      <n-popover trigger="hover">
        <template #trigger>
          <div class="createJobBtn" @click="openCreateManual">
            <n-icon :size="80">
              <FileAddOutlined />
            </n-icon>
          </div>
        </template>
        <span>创建手工测试任务</span>
      </n-popover>
    </div>
  </div>
  <excute-drawer ref="excuteDrawerRef" />

  <result-count-drawer ref="resultCountDrawerRef" />

  <manual-createModal
    ref="manualCreateModalRef"
    @updateTable="() => executeRef.getData()"
  ></manual-createModal>
</template>

<script>
import { FileAddOutlined } from '@vicons/antd';
import ManualList from '@/views/testCenter/manual/components/ManualList.vue';
import ManualCreateModal from '@/views/testCenter/manual/components/ManualCreateModal.vue';
import ExcuteDrawer from '@/views/testCenter/manual/components/ExcuteDrawer.vue';
import ResultCountDrawer from '@/views/testCenter/manual/components/ResultCountDrawer.vue';
import { manual } from './modules';
export default defineComponent({
  components: {
    ManualList,
    ManualCreateModal,
    FileAddOutlined,
    ExcuteDrawer,
    ResultCountDrawer,
  },

  setup() {
    onMounted(() => {});
    return {
      ...manual,
    };
  },
});
</script>

<style lang="less">
.manualContainer {
  display: flex;
  padding: 20px;

  .title {
    font-size: 30px;
    font-weight: 600;
  }

  .secondTitle {
    font-size: 18px;
    display: inline-block;

    .selectNum {
      display: inline-block;
      width: 80px;
    }
  }

  .searchInput {
    width: 100%;
  }

  .anchorWrap {
    width: 144px;
    display: flex;
    flex-direction: column;
    align-items: center;
    flex-shrink: 0;

    .anchor {
      z-index: 1;
      position: fixed;
    }

    .createJobBtn {
      position: fixed;
      bottom: 300px;
      color: #cecece;
      cursor: pointer;
      &:hover {
        color: grey;
      }
    }
  }
}
</style>
