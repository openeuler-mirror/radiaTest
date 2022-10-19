<template>
  <n-grid :cols="24" :y-gap="6" style="padding-top: 20px">
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
    <n-gi :span="16"> </n-gi>
    <n-gi :span="2">
      <div class="titleBtnWrap">
        <filterButton class="item" :filterRule="filterRule" @filterchange="filterchange"></filterButton>
        <refresh-button @refresh="tableRef.getData()"> 刷新虚拟机列表 </refresh-button>
      </div>
    </n-gi>
    <n-gi :span="24"></n-gi>
    <n-gi :span="24"></n-gi>
    <n-gi :span="24">
      <vmachine-table ref="tableRef" @update="() => updateModalRef.show()" />
      <modal-card title="修改虚拟机IP" ref="ipaddrModalRef" @validate="submitIpaddr">
        <template #form>
          <n-form :model="ipaddr" :rules="ipaddrRule">
            <n-form-item path="ip" label="虚拟机IP地址">
              <n-input style="width: 100%" v-model:value="ipaddr.ip" placeholder="请确保手动录入的IP有效" />
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
</template>

<script>
import { ref, defineComponent } from 'vue';

import settings from '@/assets/config/settings.js';
import Common from '@/components/CRUD';
import Essential from '@/components/vmachineComponents';
import {
  ipaddrModalRef,
  delayModalRef,
  ipaddr,
  delay,
  submitIpaddr,
  submitDelay,
  ipaddrRule
} from './modules/vmachineTableColumns';
import filterButton from '@/components/filter/filterButton.vue';
import { useStore } from 'vuex';
import vmachineFilter from '@/views/vmachine/modules/vmachineFilter.js';

export default defineComponent({
  components: {
    ...Common,
    ...Essential,
    filterButton
  },
  // eslint-disable-next-line max-lines-per-function
  setup() {
    const tableRef = ref(null);
    const createFormRef = ref(null);
    const updateFormRef = ref(null);
    const createModalRef = ref(null);
    const updateModalRef = ref(null);
    const store = useStore();
    const filterRule = ref([
      {
        path: 'name',
        name: '虚拟机名称',
        type: 'input'
      },
      {
        path: 'ip',
        name: 'IP地址',
        type: 'input'
      },
      {
        path: 'frame',
        name: '架构',
        type: 'select',
        options: [
          { label: 'aarch64', value: 'aarch64' },
          { label: 'x86_64', value: 'x86_64' }
        ]
      },
      {
        path: 'host_ip',
        name: '宿主机IP',
        type: 'input'
      },
      {
        path: 'description',
        name: '使用描述',
        type: 'input'
      }
    ]);

    const filterchange = (filterArray) => {
      tableRef.value.pagination.page = 1;
      vmachineFilter.filterValue.value = {
        name: null,
        frame: null,
        ip: null,
        host_ip: null,
        description: null
      };
      filterArray.forEach((v) => {
        vmachineFilter.filterValue.value[v.path] = v.value;
      });

      store.commit('filterVm/setAll', vmachineFilter.filterValue.value);
    };

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
      filterRule,
      filterchange
    };
  }
});
</script>

<style scoped lang="less">
.titleBtnWrap {
  display: flex;
  align-items: center;

  .item {
    margin: 0 20px;
  }
}
</style>
