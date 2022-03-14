<template>
  <div>
    <n-h3 style="display: flex; align-items: center">
      <n-icon size="20" style="margin-right: 10px">
        <GroupsFilled />
      </n-icon>
      {{ groupName }}
    </n-h3>
    <div style="margin-bottom: 10px">
      <n-button @click="addFramework" type="primary">
        添加测试框架
        <template #icon>
          <n-icon><Add /></n-icon>
        </template>
      </n-button>
    </div>
    <n-data-table
      :row-props="frameRowProps"
      :pagination="frameworkPagination"
      :columns="frameworkColumns"
      :data="frameworkData"
      :row-key="(row) => row.id"
      :loading = "frameLoading"
      remote
    />
    <n-modal
      v-model:show="showModal"
      preset="dialog"
      :title="isCreate ? '新增测试框架' : '修改测试框架'"
    >
      <n-form
        ref="formRef"
        label-placement="top"
        :model="frameworkForm"
        :rules="frameworkRules"
      >
        <n-form-item label="名称" path="name">
          <n-input
            v-model:value="frameworkForm.name"
            placeholder="请输入名称"
          />
        </n-form-item>
        <n-form-item label="仓库地址" path="url">
          <n-input v-model:value="frameworkForm.url" placeholder="仓库地址" />
        </n-form-item>
        <n-form-item
          label="日志目录相对路径(相对仓库地址根路径)"
          path="logs_path"
        >
          <n-input
            v-model:value="frameworkForm.logs_path"
            placeholder="日志目录相对路径"
          />
        </n-form-item>
        <n-form-item label="是否已适配" path="adaptive">
          <n-switch v-model:value="frameworkForm.adaptive">
            <template #checked> 是 </template>
            <template #unchecked> 否 </template>
          </n-switch>
        </n-form-item>
      </n-form>
      <template #action>
        <n-space style="width: 100%">
          <n-button type="error" ghost size="large" @click="closeForm">
            取消
          </n-button>
          <n-button size="large" @click="submitForm" type="primary" ghost>
            提交
          </n-button>
        </n-space>
      </template>
    </n-modal>
    <n-modal
      v-model:show="repoModal"
      preset="dialog"
      :title="isRepoCreate ? '新增代码仓' : '修改代码仓'"
    >
      <n-form
        ref="repoRef"
        label-placement="top"
        :model="repoForm"
        :rules="repoRules"
      >
        <n-form-item label="名称" path="name">
          <n-input
            v-model:value="repoForm.name"
            placeholder="请输入名称"
          />
        </n-form-item>
        <n-form-item label="仓库地址" path="git_url">
          <n-input v-model:value="repoForm.git_url" placeholder="仓库地址" />
        </n-form-item>
        <n-form-item label="是否允许同步" path="sync_rule">
          <n-switch v-model:value="repoForm.sync_rule">
            <template #checked> 是 </template>
            <template #unchecked> 否 </template>
          </n-switch>
        </n-form-item>
      </n-form>
      <template #action>
        <n-space style="width: 100%">
          <n-button type="error" ghost size="large" @click="closeRepoForm">
            取消
          </n-button>
          <n-button size="large" @click="submitRepoForm" type="primary" ghost>
            提交
          </n-button>
        </n-space>
      </template>
    </n-modal>
  </div>
</template>
<script>
import { modules } from './modules/index';
import { Add } from '@vicons/ionicons5';
import { GroupsFilled } from '@vicons/material';
export default {
  components: { Add, GroupsFilled },
  setup() {
    modules.initData();
    return {
      ...modules
    };
  }
};
</script>
