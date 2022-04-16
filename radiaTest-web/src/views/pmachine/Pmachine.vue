<template>
  <selection-button
    @show="tableRef.showSelection()"
    @off="tableRef.offSelection()"
  />
  <n-grid x-gap="24" y-gap="6">
    <n-gi :span="6">
      <n-space>
        <create-button title="注册物理机" @click="createModalRef.show()" />
        <modal-card
          :initY="100"
          :initX="500"
          title="注册物理机"
          url="/v1/pmachine"
          ref="createModalRef"
          @validate="() => createFormRef.handlePropsButtonClick()"
          @submit="createFormRef.post()"
        >
          <template #form>
            <n-tabs
              type="line"
              size="large"
              :tab-padding="20"
              @update:value="
                (value) => {
                  createFormRef.changeTabs(value);
                }
              "
            >
              <n-tab-pane
                tab="基本参数"
                name="basic"
                @click="createFormRef.changeTabs('basic')"
              >
                <div></div>
              </n-tab-pane>
              <n-tab-pane
                tab="SSH参数"
                name="ssh"
                @click="createFormRef.changeTabs('ssh')"
              >
                <div></div>
              </n-tab-pane>
            </n-tabs>
            <pmachine-create-form
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
        <delete-button title="物理机" url="/pmachine" />
      </n-space>
    </n-gi>
    <n-gi :span="18">
      <n-space justify="end">
        <pmachine-batch-button-group />
        <refresh-button @refresh="tableRef.getData()">
          刷新物理机列表
        </refresh-button>
      </n-space>
    </n-gi>
    <n-gi :span="24"></n-gi>
    <n-gi :span="24"></n-gi>
    <n-gi :span="24">
      <pmachine-filter />
    </n-gi>
    <n-gi :span="24">
      <pmachine-table ref="tableRef" @update="() => updateModalRef.show()" />
      <modal-card
        title="修改物理机"
        url="/v1/pmachine"
        ref="updateModalRef"
        @validate="() => updateFormRef.handlePropsButtonClick()"
        @submit="updateFormRef.put()"
      >
        <template #form>
          <n-tabs
            type="line"
            size="large"
            :tab-padding="20"
            @update:value="
              (value) => {
                updateFormRef.changeTabs(value);
              }
            "
          >
            <n-tab-pane tab="基本参数" name="basic">
              <div></div>
            </n-tab-pane>
            <n-tab-pane tab="BMC参数" name="bmc">
              <div></div>
            </n-tab-pane>
            <n-tab-pane tab="SSH参数" name="ssh">
              <div></div>
            </n-tab-pane>
          </n-tabs>
          <pmachine-update-form
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
    </n-gi>
  </n-grid>
  <!-- <n-card
    size="huge"
    :segmented="{
      content: 'hard',
    }"
    header-style="
            font-size: 30px; 
            height: 80px; 
            font-family: 'v-sans';
            background-color: rgb(242,242,242);
        "
    style="height: 100%"
  >
    
    <template #action>
      <n-divider />
      <div
        style="
          text-align: center;
          color: grey;
          padding-top: 15px;
          padding-bottom: 0;
        "
      >
        {{ settings.name }} {{ settings.version }} · {{ settings.license }}
      </div>
    </template>
  </n-card> -->
</template>

<script>
import { ref, defineComponent } from 'vue';

import settings from '@/assets/config/settings.js';
import Common from '@/components/CRUD';
import Essential from '@/components/pmachineComponents';

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

<style scoped></style>
