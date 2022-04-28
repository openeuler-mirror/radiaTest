<template>
  <div style="padding: 28px 40px">
    <n-grid x-gap="24" y-gap="6">
      <n-gi :span="12">
        <n-space>
          <!-- <n-button
            @click="createModalRef.show()"
            size="large"
            type="primary"
            strong
            round
          >
            <template #icon>
              <file-plus />
            </template>
            创建用例
          </n-button> -->
          <modal-card
            :initY="100"
            :initX="300"
            title="新建文本用例"
            ref="createModalRef"
            @validate="() => createFormRef.handlePropsButtonClick()"
            @submit="createFormRef.post()"
          >
            <template #form>
              <n-tabs
                type="line"
                size="large"
                :tab-padding="20"
                @update:value="(value) => createFormRef.changeTabs(value)"
              >
                <n-tab-pane
                  name="info"
                  tab="基本信息"
                  @click="createFormRef.changeTabs('info')"
                >
                  <div></div>
                </n-tab-pane>
                <n-tab-pane
                  name="content"
                  tab="详细内容"
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
          <!-- <n-button
            @click="importModalRef.show()"
            size="large"
            type="info"
            strong
            round
          >
            <template #icon>
              <file-import />
            </template>
            导入用例
          </n-button> -->
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
                ref="importFormRef"
                @valid="() => importModalRef.submitCreateForm()"
                @close="
                  () => {
                    importModalRef.close();
                  }
                "
              />
            </template>
          </modal-card>
        </n-space>
      </n-gi>
      <n-gi :span="12">
        <n-space justify="end">
          <refresh-button @refresh="tableRef.refreshData()">
            刷新版本列表
          </refresh-button>
        </n-space>
      </n-gi>
      <n-gi :span="24">
        <testcase-filter style="position: relative" />
      </n-gi>
      <n-gi :span="24">
        <testcase-table ref="tableRef" @update="() => updateModalRef.show()" />
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
        <extend-drawer />
      </n-gi>
    </n-grid>
  </div>
</template>

<script>
import { ref, defineComponent } from 'vue';

import settings from '@/assets/config/settings.js';
import Common from '@/components/CRUD';
import Essential from '@/components/testcaseComponents';
// import { FileImport, FilePlus } from '@vicons/tabler';

export default defineComponent({
  components: {
    ...Common,
    ...Essential,
  },
  setup() {
    const tableRef = ref(null);
    const createFormRef = ref(null);
    const importFormRef = ref(null);
    const updateFormRef = ref(null);
    const createModalRef = ref(null);
    const importModalRef = ref(null);
    const updateModalRef = ref(null);

    return {
      settings,
      tableRef,
      createFormRef,
      importFormRef,
      updateFormRef,
      createModalRef,
      importModalRef,
      updateModalRef,
    };
  },
});
</script>

<style scoped></style>
