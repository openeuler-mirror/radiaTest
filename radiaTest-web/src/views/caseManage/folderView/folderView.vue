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
          animated
          type="line"
          size="large"
          :tab-padding="20"
          @update:value="(value) => createFormRef.changeTabs(value)"
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
          @valid="
            () => {
              importModalRef.submitCreateForm();
              importModalRef.close();
            }
          "
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
    <create-suites />
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
        <n-alert title="用例导入须知" type="warning" closable>
          请确保文本用例格式与模板一致，否则导入时将会被跳过。点击<a :href="caseTemplateUrl">下载</a
          >文本用例模板文件
        </n-alert>

        <tree
          :expandKeys="expandKeys"
          :data="menuList"
          @load="loadData"
          @selectAction="selectAction"
          @menuClick="menuClick"
          :selectKey="selectKey"
          @expand="expand"
        />
        <tree
          :expandKeys="expandKeys"
          :data="releaseMenu"
          @load="loadData"
          @selectAction="selectAction"
          @menuClick="menuClick"
          :selectKey="selectKey"
          @expand="expand"
          v-if="$route.params.workspace === 'release'"
        />
        <!--        TODO:匹配对应版本和阶段-->
      </n-layout-sider>
      <n-layout-content
        content-style="padding: 24px;"
        :style="{ height: contentHeight + 'px', overflowY: 'auto' }"
        id="folderviewRight"
      >
        <router-view :key="key" />
      </n-layout-content>
    </n-layout>
  </n-spin>
</template>
<script>
import tree from '@/components/tree/tree.vue';
import { modules } from './modules';
import config from '@/assets/config/settings.js';
import Common from '@/components/CRUD';
import Essential from '@/components/testcaseComponents';
import { ref } from 'vue';
import testsuiteCreate from '@/components/testsuiteComponents/testsuiteCreate.vue';
import createDrawer from '@/components/task/createDrawer.vue';
import createSuites from './createSuites/CreateSuites';
import { getFramework } from '@/api/get';

export default {
  components: {
    ...Common,
    ...Essential,
    createDrawer,
    tree,
    testsuiteCreate,
    createSuites,
  },
  computed: {
    key() {
      return this.$route.path + new Date();
    },
  },
  mounted() {
    getFramework().then((res) => {
      this.frameworkList = res.data?.map((item) => ({
        label: item.name,
        value: item.id,
        isLeaf: false,
      }));
    });
    this.contentHeight =
      document.body.clientHeight -
      document.getElementById('header').clientHeight -
      document.querySelector('.n-card-header').clientHeight -
      10;

    this.$nextTick(() => {
      window.addEventListener('refreshEvent', ({ detail }) => {
        this.expandNode(detail.caseNodeId);
      });
      window.addEventListener('rootRefreshEvent', ({ detail }) => {
        this.expandRoot(detail.type, detail.id);
      });
    });
  },
  setup() {
    const caseTemplateUrl = `https://${config.serverPath}/static/case_template.xls`;
    modules.clearSelectKey();
    modules.getRootNodes();

    const contentHeight = ref(0);
    return {
      caseTemplateUrl,
      contentHeight,
      ...modules,
    };
  },
};
</script>
<style lang="less" scope>
.n-layout-sider-scroll-container::-webkit-scrollbar {
  display: none;
}
.n-tree {
  width: 100%;
  overflow-x: scroll;
}
.n-tree .n-tree-node {
  word-break: initial;
}
</style>
