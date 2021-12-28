<template>
  <div class="container">
    <n-drawer
      v-model:show="showNewTemplateDrawer"
      :maskClosable="false"
      width="324px"
      placement="right"
    >
      <n-drawer-content :title="drawerTitle">
        <n-form
          :model="drawerModel"
          :rules="drawerRules"
          ref="templateFormRef"
          label-placement="left"
          :label-width="80"
          size="medium"
          :style="{}"
        >
          <n-form-item label="模板名称" path="templateName">
            <n-input
              placeholder="请输入模板名称"
              v-model:value="drawerModel.templateName"
              :disabled="
                drawerType === 'newTemplateType' ||
                  drawerType === 'editTemplateType'
              "
            />
          </n-form-item>
          <n-form-item
            label="团队名称"
            path="groupName"
            v-if="drawerType !== 'editTemplateName'"
          >
            <n-select
              v-model:value="drawerModel.groupName"
              placeholder="请选择团队"
              :options="groupNameOptions"
              @update:value="handleChangeGroup"
              clearable
              :disabled="
                drawerType === 'newTemplateType' ||
                  drawerType === 'editTemplateType'
              "
            />
          </n-form-item>
          <n-form-item
            label="模板类型"
            path="templateType"
            v-if="drawerType !== 'editTemplateName'"
          >
            <n-input
              placeholder="请输入模板名称"
              v-model:value="drawerModel.templateType"
            />
          </n-form-item>
          <n-form-item
            label="测试套"
            path="suiteNames"
            v-if="drawerType !== 'editTemplateName'"
          >
            <n-select
              v-model:value="drawerModel.suiteNames"
              multiple
              filterable
              placeholder="请选择测试套"
              :options="suiteNamesOptions"
              clearable
              remote
              @search="handleSuiteNamesSearch"
            />
          </n-form-item>
          <n-form-item
            label="责任人"
            path="executor"
            v-if="drawerType !== 'editTemplateName'"
          >
            <n-select
              placeholder="请选择责任人"
              filterable
              clearable
              remote
              :options="executorOptions"
              @search="handleExecutorSearch"
              v-model:value="drawerModel.executor"
              @update:value="handleChangeExecutor"
            />
          </n-form-item>
          <n-form-item
            label="协助人"
            path="helper"
            v-if="drawerType !== 'editTemplateName'"
          >
            <n-select
              v-model:value="drawerModel.helpers"
              multiple
              filterable
              placeholder="请选择协助人"
              :options="helpersOptions"
              clearable
              remote
              @search="handleHelpersSearch"
              @update:value="handleChangeHelper"
            />
          </n-form-item>
          <div class="createButtonBox">
            <n-button
              class="btn"
              type="error"
              ghost
              @click="cancelCreateTemplate"
              >取消</n-button
            >
            <n-button
              class="btn"
              type="info"
              ghost
              @click="createTemplate"
              v-show="drawerType === 'newTemplate'"
              >创建模板</n-button
            >
            <n-button
              class="btn"
              type="info"
              ghost
              @click="createTemplateType"
              v-show="drawerType === 'newTemplateType'"
              >新增类型</n-button
            >
            <n-button
              class="btn"
              type="info"
              ghost
              @click="editTemplateNameCb"
              v-show="drawerType === 'editTemplateName'"
              >修改名称</n-button
            >
            <n-button
              class="btn"
              type="info"
              ghost
              @click="editTemplateTypeCb"
              v-show="drawerType === 'editTemplateType'"
              >修改类型</n-button
            >
          </div>
        </n-form>
      </n-drawer-content>
    </n-drawer>
    <div class="addTemplateWrap">
      <n-button
        @click="showAddTemplateBtn"
        size="large"
        type="info"
        strong
        round
      >
        <template #icon>
          <file-plus />
        </template>
        创建模板
      </n-button>
    </div>
    <n-scrollbar style="max-height: 800px;">
      <n-data-table
        remote
        :loading="distributionLoading"
        :columns="distributionColumns"
        :data="distributionTableData"
        :single-line="false"
        :pagination="templatePagination"
        @update:page="handleTemplatePageChange"
      />
    </n-scrollbar>
  </div>
</template>

<script>
import { modules } from './modules/index.js';
import { FilePlus } from '@vicons/tabler';

export default {
  components: {
    FilePlus,
  },
  setup() {
    modules.init();

    return modules;
  },
};
</script>

<style scoped lang="less">
.container {
  display: flex;
  flex-direction: column;

  .addTemplateWrap {
    margin-bottom: 15px;
  }
}

.createButtonBox {
  display: flex;
  justify-content: space-evenly;
  .btn {
    width: 100px;
  }
}

.trigger {
  margin: 0;
  width: 195px;
  text-overflow: ellipsis;
  overflow: hidden;
  white-space: nowrap;
}
</style>
