<template>
  <n-spin :show="showLoading" stroke="rgba(0, 47, 167, 1)">
    <modal-card
      :initY="100"
      :initX="300"
      title="新建文本用例"
      ref="createModalRef"
      @validate="() => createFormRef.handlePropsButtonClick()"
      @submit="submitCreateCase"
    >
      <template #form>
        <n-tabs 
          type="line" 
          size="large" 
          :tab-padding="20"  
          @update:value="(value)=>createFormRef.changeTabs(value)"
        >
          <n-tab-pane tab="基本信息" name="basic">
            <div></div>
          </n-tab-pane>
          <n-tab-pane tab="详细内容" name="detail">
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
    <modal-card
      :initY="100"
      :initX="300"
      title="修改测试套"
      ref="putModalRef"
      @validate="() => putFormRef.put()"
    >
      <template #form>
        <testsuite-create
          ref="putFormRef"
          :data="suiteInfo"
          @close="
            () => {
              putModalRef.close();
            }
          "
        />
      </template>
    </modal-card>
    <modal-card
      :initY="200"
      :initX="600"
      title="导入文本用例"
      ref="importModalRef"
      @validate="() => importFormRef.handlePropsButtonClick()"
      @submit="importFormRef.post()"
    >
      <template #form>
        <testcase-import-form
          :showGroup="false"
          ref="importFormRef"
          @submitForm="extendSubmit"
          @valid="() => importModalRef.submitCreateForm()"
          @close="
            () => {
              importModalRef.close();
            }
          "
        />
      </template>
    </modal-card>
    <modal-card
      :initX="300"
      title="修改文本用例"
      ref="updateModalRef"
      @validate="() => updateFormRef.handlePropsButtonClick()"
      @submit="updateFormRef.put()"
    >
      <template #form>
        <testcase-update-form
          ref="updateFormRef"
          @valid="() => updateModalRef.submitCreateForm()"
          @close="
            () => {
              updateModalRef.close();
            }
          "
        />
      </template>
    </modal-card>
    <create-drawer :isCase="true" ref="createTaskForm" @submit="createRelationTask" />
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
  </n-spin>
</template>
<script>
import tree from '@/components/tree/tree.vue';
import { modules } from './modules';
import Common from '@/components/CRUD';
import Essential from '@/components/testcaseComponents';
import { ref } from 'vue';
import testsuiteCreate from '@/components/testsuiteComponents/testsuiteCreate.vue';
import createDrawer from '@/components/task/createDrawer.vue';
export default {
  components: {
    ...Common,
    ...Essential,
    createDrawer,
    tree,
    testsuiteCreate
  },
  computed: {
    key() {
      return this.$route.path + new Date();
    },
  },
  mounted() {
    this.$axios.get('/v1/framework').then((res) => {
      this.frameworkList = res.data?.map((item) => ({
        label: item.name,
        value: item.id,
        isLeaf: false
      }));
    });
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
