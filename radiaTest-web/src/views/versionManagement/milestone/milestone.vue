<template>
  <modal-card
    title="注册里程碑"
    url="/v2/milestone"
    ref="createModalRef"
    @validate="() => createFormRef.handlePropsButtonClick()"
    @submit="createFormRef.post()"
  >
    <template #form>
      <milestone-create-form
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
  <div class="milestone-head">
    <div>
      <create-button title="注册里程碑" @click="createModalRef.show()" />
    </div>
  </div>
  <n-grid x-gap="24">
    <n-gi :span="24">
      <milestone-table ref="tableRef" @update="() => updateModalRef.show()" />
      <modal-card
        title="修改里程碑"
        url="/v2/milestone"
        ref="updateModalRef"
        @validate="() => updateFormRef.handlePropsButtonClick()"
        @submit="updateFormRef.put()"
      >
        <template #form>
          <milestone-update-form
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
</template>

<script>
import { ref, defineComponent } from 'vue';

import settings from '@/assets/config/settings.js';
import Common from '@/components/CRUD';
import Essential from '@/components/milestoneComponents';

export default defineComponent({
  components: {
    ...Common,
    ...Essential,
  },
  setup() {
    const tableRef = ref(null);
    const createFormRef = ref(null);
    const updateFormRef = ref(null);
    const createModalRef = ref(null);
    const updateModalRef = ref(null);

    return {
      settings,
      tableRef,
      createFormRef,
      updateFormRef,
      createModalRef,
      updateModalRef,
    };
  },
});
</script>

<style scoped>
.milestone-head {
  display: flex;
  justify-content: space-between;
  margin: 10px 0;
}
</style>