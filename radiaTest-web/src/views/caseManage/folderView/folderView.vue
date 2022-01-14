<template>
  <modal-card
    :initY="100"
    :initX="300"
    title="新建文本用例"
    ref="createModalRef"
    @validate="() => createFormRef.handlePropsButtonClick()"
    @submit="submitCreateCase"
  >
    <template #form>
      <n-tabs type="line" size="large" :tab-padding="20">
        <n-tab-pane name="基本信息" @click="createFormRef.changeTabs('info')">
          <div></div>
        </n-tab-pane>
        <n-tab-pane
          name="详细内容"
          @click="createFormRef.changeTabs('content')"
        >
          <div></div>
        </n-tab-pane>
      </n-tabs>
      <testcase-create-form
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
  <n-layout has-sider>
    <n-layout-sider
      bordered
      content-style="padding: 24px;overflow-y:auto;"
      collapse-mode="width"
      :collapsed-width="1"
      :width="400"
      show-trigger="arrow-circle"
      :style="{ height: contentHeight + 'px' }"
    >
      <tree
        :expandKeys="expandKeys"
        :data="menuList"
        @load="loadData"
        @selectAction="selectAction"
        @menuClick="menuClick"
        :selectKey="selectKey"
        @expand="expand"
      />
    </n-layout-sider>
    <n-layout-content
      content-style="padding: 24px;"
      :style="{ height: contentHeight + 'px', overflowY: 'auto' }"
    >
      <router-view :key="key" />
    </n-layout-content>
  </n-layout>
</template>
<script>
import tree from '@/components/tree/tree.vue';
import { modules } from './modules';
import Common from '@/components/CRUD';
import Essential from '@/components/testcaseComponents';
import { ref } from 'vue';
export default {
  components: {
    ...Common,
    ...Essential,
    tree,
  },
  computed: {
    key() {
      return this.$route.path + new Date();
    },
  },
  mounted() {
    this.contentHeight =
      document.body.clientHeight -
      document.getElementById('header').clientHeight -
      document.querySelector('.n-card-header').clientHeight -
      document.querySelector('.n-card__action').clientHeight -
      10;
    this.$nextTick(() => {
      window.addEventListener('refreshEvent', ({ detail }) => {
        this.expandNode(detail.baselineId);
      });
    });
  },
  setup() {
    modules.clearSelectKey();
    if (!modules.menuList.value) {
      modules.getOrg();
    }
    const contentHeight = ref(0);
    return {
      contentHeight,
      ...modules,
    };
  },
};
</script>
<style lang="less">
.n-layout-sider-scroll-container::-webkit-scrollbar {
  display: none;
}
</style>
