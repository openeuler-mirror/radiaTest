<template>
  <n-grid x-gap="24" y-gap="6" style="padding-top:20px">
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
              <n-tab-pane tab="基本参数" name="basic">
                <div></div>
              </n-tab-pane>
              <n-tab-pane tab="SSH参数" name="ssh">
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
        <delete-button title="物理机" url="/v1/pmachine" />
      </n-space>
    </n-gi>
    <n-gi :span="15"> </n-gi>
    <n-gi :span="3">
      <div class="titleBtnWrap">
        <selection-button @show="tableRef.showSelection()" @off="tableRef.offSelection()" />
        <filterButton class="item" :filterRule="filterRule" @filterchange="filterchange"></filterButton>
        <refresh-button @refresh="tableRef.getData()">
          刷新物理机列表
        </refresh-button>
      </div>
    </n-gi>
    <n-gi :span="24"></n-gi>
    <n-gi :span="24"></n-gi>
    <n-gi :span="24">
      <pmachine-table ref="tableRef" @update="() => updateModalRef.show()" />
      <modal-card title="延长占用时间" ref="delayModalRef" @validate="submitDelay">
        <template #form>
          <n-form-item label="释放时间">
            <n-date-picker style="width: 100%" v-model:value="delay.time" type="date" :is-date-disabled="(current) => delay.time > current" />
          </n-form-item>
        </template>
      </modal-card>
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
import { delay, delayModalRef, submitDelay } from './modules/pmachineTableColumns';
import filterButton from '@/components/filter/filterButton.vue';
import { useStore } from 'vuex';
import pmachineFilter from '@/views/pmachine/modules/pmachineFilter.js';

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

    const macInputCb = (inputItem) => {
      if ((inputItem.value.length - 1) % 3 === 2 && inputItem.value.length < 18) {
        inputItem.value = `${inputItem.value.substr(0, inputItem.value.length - 1)}:${inputItem.value.substr(inputItem.value.length - 1, 1)}`;
      } else if (inputItem.value.length === 18) {
        inputItem.value = inputItem.value.substr(0, 17);
      }
      if (inputItem.value.substr(inputItem.value.length - 2, 2) === '::') {
        inputItem.value = inputItem.value.substr(0, inputItem.value.length - 2);
      }
    };

    const filterRule = ref([
      {
        path: 'mac',
        name: 'MAC地址',
        type: 'input',
        cb: macInputCb
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
        path: 'sshIp',
        name: 'IP地址',
        type: 'input'
      },
      {
        path: 'bmcIp',
        name: 'BMC IP',
        type: 'input'
      },
      {
        path: 'occupier',
        name: '当前使用人',
        type: 'input'
      },
      {
        path: '_state',
        name: '占用状态',
        type: 'select',
        options: [
          { label: '占用', value: 'occupied' },
          { label: '释放', value: 'idle' }
        ]
      },
      {
        path: 'description',
        name: '使用说明',
        type: 'input'
      }
    ]);

    const filterchange = (filterArray) => {
      pmachineFilter.filterValue.value = {
        mac: '',
        frame: null,
        _state: null,
        sshIp: '',
        bmcIp: '',
        description: '',
        occupier: ''
      };
      filterArray.forEach((v) => {
        pmachineFilter.filterValue.value[v.path] = v.value;
      });

      store.commit('filterPm/setAll', pmachineFilter.filterValue.value);
    };

    return {
      delay,
      delayModalRef,
      submitDelay,
      settings,
      tableRef,
      createFormRef,
      updateFormRef,
      createModalRef,
      updateModalRef,
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
