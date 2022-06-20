<template>
  <n-grid :cols="24" :y-gap="6" style="padding-top:20px">
    <n-gi :span="6">
      <n-space>
        <create-button title="注册虚拟机" @click="createModalRef.show()" />
        <modal-card
          title="注册虚拟机"
          url="/v1/vmachine"
          ref="createModalRef"
          @validate="() => createFormRef.handlePropsButtonClick()"
          @submit="createFormRef.post()"
        >
          <template #form>
            <vmachine-create-form
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
      </n-space>
    </n-gi>
    <n-gi :span="17">
      <vmachine-filter />
    </n-gi>
    <n-gi :span="1">
      <n-space justify="end">
        <refresh-button @refresh="tableRef.getData()">
          刷新虚拟机列表
        </refresh-button>
      </n-space>
    </n-gi>
    <n-gi :span="24"></n-gi>
    <n-gi :span="24"></n-gi>
    <n-gi :span="24">
      <vmachine-table ref="tableRef" @update="() => updateModalRef.show()" />
      <modal-card title="修改虚拟机IP" ref="ipaddrModalRef" @validate="submitIpaddr">
        <template #form>
          <n-form :model="ipaddr" :rules="ipaddrRule">
            <n-form-item path="ip" label="虚拟机IP地址">
              <n-input 
                style="width: 100%"
                v-model:value="ipaddr.ip"
                placeholder="请确保手动录入的IP有效"
              />
            </n-form-item>
          </n-form>
        </template>
      </modal-card>
      <modal-card title="延期" ref="delayModalRef" @validate="submitDelay">
        <template #form>
          <n-form-item label="释放时间">
            <n-date-picker
              style="width: 100%"
              v-model:value="delay.time"
              type="date"
              :is-date-disabled="(current) => delay.time > current"
            />
          </n-form-item>
        </template>
      </modal-card>
      <modal-card
        title="修改虚拟机"
        url="/v1/vmachine"
        ref="updateModalRef"
        @validate="() => updateFormRef.handlePropsButtonClick()"
        @submit="updateFormRef.put()"
      >
        <template #form>
          <vmachine-update-form
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
import Essential from '@/components/vmachineComponents';
import { ipaddrModalRef, delayModalRef, ipaddr, delay, submitIpaddr, submitDelay, ipaddrRule } from './modules/vmachineTableColumns';
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
      ipaddrRule,
      createFormRef,
      updateFormRef,
      createModalRef,
      updateModalRef,
      ipaddrModalRef,
      delayModalRef,
      submitIpaddr,
      submitDelay,
      ipaddr,
      delay,
    };
  },
});
</script>

<style scoped></style>
