<template>
  <div style="padding:28px 40px">
    <n-grid x-gap="24" y-gap="6">
      <n-gi :span="12">
        <n-space>
          <n-button
            @click="createModalRef.show()"
            size="large"
            type="primary"
            strong
            round
          >
            <template #icon>
              <file-plus />
            </template>
            创建测试套
          </n-button>
          <modal-card
            :initY="100"
            :initX="300"
            title="新建测试套"
            ref="createModalRef"
            @validate="() => createFormRef.post()"
          >
            <template #form>
              <testsuite-create
                ref="createFormRef"
                @close="
                  () => {
                    createModalRef.close();
                  }
                "
              />
            </template>
          </modal-card>
        </n-space>
      </n-gi>
      <n-gi :span="12">
        <n-space justify="end">
          <refresh-button @refresh="tableRef.getData()">
            刷新测试套列表
          </refresh-button>
        </n-space>
      </n-gi>
      <n-gi :span="24">
        <testsuite-table ref="tableRef" @update="() => updateModalRef.show()" />
      </n-gi>
    </n-grid>
  </div>
</template>

<script>
import { ref, defineComponent } from 'vue';

import settings from '@/assets/config/settings.js';
import Common from '@/components/CRUD';
import Essential from '@/components/testcaseComponents';
import testsuiteCreate from '@/components/testsuiteComponents/testsuiteCreate.vue';
import {  FilePlus } from '@vicons/tabler';
import testsuiteTable from '@/components/testsuiteComponents/testsuiteTable.vue';

export default defineComponent({
  components: {
    testsuiteCreate,
    testsuiteTable,
    ...Common,
    ...Essential,
    FilePlus,
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
