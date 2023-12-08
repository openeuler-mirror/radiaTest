<template>
  <n-scrollbar style="max-height: 730px">
    <n-form
      :label-width="100"
      :model="formValue"
      :rules="rules"
      :size="size"
      label-placement="top"
      ref="formRef"
      class="batch-form"
    >
      <n-grid :cols="24" :x-gap="20">
        <n-form-item-gi :span="5" label="创建方法" path="method">
          <n-select
            v-model:value="formValue.method"
            :options="[
              {
                label: 'qcow2镜像导入',
                value: 'import',
              },
              {
                label: '虚拟光驱安装',
                value: 'cdrom',
              },
              {
                label: '自动安装',
                value: 'auto',
              },
            ]"
            placeholder="选择创建方法"
          />
        </n-form-item-gi>
        <n-form-item-gi :span="5" label="产品" path="product">
          <n-select
            v-model:value="formValue.product"
            :options="productOpts"
            placeholder="选择产品"
            filterable
          />
        </n-form-item-gi>
        <n-form-item-gi :span="5" label="版本" path="version">
          <n-select
            v-model:value="formValue.version"
            :options="versionOpts"
            placeholder="选择版本"
            filterable
          />
        </n-form-item-gi>
        <n-form-item-gi :span="6" label="里程碑" path="milestone_id">
          <n-select
            v-model:value="formValue.milestone_id"
            :options="milestoneOpts"
            placeholder="选择里程碑"
            filterable
            @update:value="handleUpdateMilestone"
          />
        </n-form-item-gi>
        <n-form-item-gi :span="3" path="version_types">
          <n-button
            attr-type="button"
            :render-icon="renderIcon"
            @click="addItem"
            :disabled="!formValue.method || !formValue.milestone_id || isIncludeMilestone"
          >
            添加虚拟机
          </n-button>
        </n-form-item-gi>
        <n-form-item-gi
          :span="12"
          v-for="(item, typeIndex) in formValue.version_types"
          :key="item.basicInfo.milestone_id"
          :show-label="false"
        >
          <n-scrollbar style="max-height: 232px">
            <n-card
              embedded
              closable
              @close="removeItem(typeIndex)"
              header-style="margin-bottom:20px"
              @click="handleClickCard(item)"
            >
              <n-ellipsis
                style="
                  max-width: 100px;
                  position: absolute;
                  top: 20px;
                  font-size: 16px;
                  left: 20px;
                  margin-bottom: 20px;
                "
              >
                {{ item.basicInfo.product }}
              </n-ellipsis>
              <n-ellipsis
                style="
                  max-width: 250px;
                  position: absolute;
                  top: 20px;
                  font-size: 16px;
                  left: 130px;
                "
              >
                {{ item.basicInfo.milestone_name }}
              </n-ellipsis>

              <n-tooltip trigger="hover">
                <template #trigger>
                  <n-icon
                    size="30"
                    style="position: absolute; top: 15px; right: 168px"
                    @click="handleClickMachineNum(item, 'add')"
                  >
                    <ArrowCircleUp20Regular />
                  </n-icon>
                </template>
                增加虚拟机数量
              </n-tooltip>

              <n-tooltip trigger="hover">
                <template #trigger>
                  <n-icon
                    size="30"
                    style="position: absolute; top: 15px; right: 140px"
                    @click="handleClickMachineNum(item, 'reduce')"
                  >
                    <ArrowCircleDown20Regular />
                  </n-icon>
                </template>
                减少虚拟机数量
              </n-tooltip>

              <n-dynamic-input
                v-model:value="item.machines"
                :on-create="createFrameAndNumber"
                style="display: flex; flex-wrap: wrap; justify-content: space-between"
                #="{ index, value }"
              >
                <n-card hoverable @click="handleClickCard(item)" style="height: 138px">
                  <div
                    v-on:dblclick="handleClick(typeIndex, index, 'expand')"
                    style="cursor: pointer; width: 215px"
                  >
                    <div>
                      {{ item.machines[index].frame }} *
                      {{ item.machines[index].machine_num || 0 }}
                    </div>
                    <div>
                      {{ item.machines[index].cpu_mode }} {{ item.machines[index].memory / 1024 }}G
                    </div>
                    <div>
                      {{
                        item.basicInfo.method === 'import'
                          ? '镜像导入'
                          : item.basicInfo.method === 'cdrom'
                          ? '光驱安装'
                          : '自动安装'
                      }}
                      HDD {{ item.machines[index].capacity || null }}GB
                    </div>
                    <div>
                      {{ item.machines[index].pm_select_mode === 'auto' ? '全自动选取' : '指定' }}
                    </div>
                    <div>
                      {{ item.machines[index].selfdescription }}
                    </div>
                    <n-tooltip trigger="hover">
                      <template #trigger>
                        <n-icon
                          size="20"
                          style="position: absolute; right: 20px; bottom: 20px"
                          @click="handleClick(typeIndex, index, 'expand')"
                        >
                          <ExpandSharp />
                        </n-icon>
                      </template>
                      修改虚拟机信息
                    </n-tooltip>
                  </div>
                  <n-modal
                    :show="boxIndex === `${typeIndex}-${index}` && configRef"
                    z-index="99999"
                  >
                    <n-card
                      style="width: 1000px"
                      :bordered="false"
                      size="huge"
                      role="dialog"
                      aria-modal="true"
                    >
                      <n-form :label-width="100" label-placement="top">
                        <n-grid :cols="24" :x-gap="20">
                          <n-form-item-gi
                            :span="4"
                            ignore-path-change
                            :path="`version_types[${typeIndex}].machines[${index}].frame`"
                            :rule="frameRule"
                            label="虚拟机架构"
                          >
                            <n-select
                              :options="frameOpts"
                              v-model:value="item.machines[index].frame"
                              placeholder="请选择架构"
                            />
                          </n-form-item-gi>
                          <n-form-item-gi
                            :span="3"
                            ignore-path-change
                            :path="`version_types[${typeIndex}].machines[${index}].machine_num`"
                            label="数量"
                          >
                            <n-input-number
                              :step="1"
                              :validator="validator"
                              :min="1"
                              :max="5"
                              v-model:value="item.machines[index].machine_num"
                              @update:value="(v) => changeFrameAndNumber(v, item.machines[index])"
                            />
                          </n-form-item-gi>
                          <n-form-item-gi
                            :span="6"
                            ignore-path-change
                            :path="`version_types[${typeIndex}].machines[${index}].cpu_mode`"
                            label="CPU Mode"
                          >
                            <n-select
                              v-model:value="item.machines[index].cpu_mode"
                              :options="[
                                { label: 'host-passthrough', value: 'host-passthrough' },
                                { label: 'host-model', value: 'host-model' },
                                { label: 'custom', value: 'custom' },
                              ]"
                              placeholder="默认 host-passthrough"
                              filterable
                            />
                          </n-form-item-gi>
                          <n-form-item-gi
                            :span="4"
                            ignore-path-change
                            :path="`version_types[${typeIndex}].machines[${index}].memory`"
                            label="内存(MB)"
                          >
                            <n-input-number
                              v-model:value="item.machines[index].memory"
                              :step="1024"
                              :validator="validator"
                              :max="16384"
                            >
                              <template #suffix>MB</template>
                            </n-input-number>
                          </n-form-item-gi>

                          <n-form-item-gi
                            :span="4"
                            label="磁盘(GiB)"
                            :path="`version_types[${typeIndex}].machines[${index}].capacity`"
                          >
                            <n-input-number
                              :disabled="formValue.method === 'import'"
                              v-model:value="item.machines[index].capacity"
                              :step="10"
                              :validator="validator"
                              :max="capacityMax"
                            >
                              <template #suffix>GiB</template>
                            </n-input-number>
                          </n-form-item-gi>
                          <n-form-item-gi
                            :span="3"
                            label="Sockets"
                            :path="`version_types[${typeIndex}].machines[${index}].sockets`"
                          >
                            <n-input-number
                              v-model:value="item.machines[index].sockets"
                              :validator="validator"
                              :min="1"
                              :max="4"
                            />
                          </n-form-item-gi>
                          <n-form-item-gi
                            :span="3"
                            label="Cores"
                            :path="`version_types[${typeIndex}].machines[${index}].cores`"
                          >
                            <n-input-number
                              v-model:value="item.machines[index].cores"
                              :validator="validator"
                              :min="1"
                              :max="4"
                            />
                          </n-form-item-gi>
                          <n-form-item-gi
                            :span="3"
                            label="Threads"
                            :path="`version_types[${typeIndex}].machines[${index}].threads`"
                          >
                            <n-input-number
                              v-model:value="item.machines[index].threads"
                              :validator="validator"
                              :min="1"
                              :max="4"
                            />
                          </n-form-item-gi>
                          <n-form-item-gi
                            :span="6"
                            label="使用描述"
                            :path="`version_types[${typeIndex}].machines[${index}].selfdescription`"
                          >
                            <n-input
                              v-model:value="item.machines[index].selfdescription"
                              placeholder="输入使用描述"
                            />
                          </n-form-item-gi>

                          <n-form-item-gi
                            :span="5"
                            label="机器调度策略"
                            :path="`version_types[${typeIndex}].machines[${index}].pm_select_mode`"
                          >
                            <n-select
                              v-model:value="item.machines[index].pm_select_mode"
                              :options="[
                                { label: '全自动选取', value: 'auto' },
                                {
                                  label: '指定',
                                  value: 'assign',
                                  disabled: item.machines[index].machine_num > 1,
                                },
                              ]"
                              placeholder="机器调度策略"
                            />
                          </n-form-item-gi>
                          <n-form-item-gi
                            :span="6"
                            label="指定物理机（需先选择架构）"
                            :path="`version_types[${typeIndex}].machines[${index}].pmachine_id`"
                            v-if="item.machines[index].pm_select_mode === 'assign'"
                          >
                            <selectMachine
                              :text="
                                item.machines[index].pmachine_id
                                  ? item.machines[index].pmachine_name
                                  : '选取物理机'
                              "
                              machineType="pm"
                              :data="pmData"
                              :checkedMachine="[item.machines[index].pmachine_id]"
                              @checked="(check) => handleCheck(check, item.machines[index])"
                              @handleShow="
                                (show) => handleUpdatePmSelectMode(show, item.machines[index])
                              "
                            />
                          </n-form-item-gi>
                          <n-form-item-gi :span="1">
                            <n-tooltip trigger="hover">
                              <template #trigger>
                                <n-icon size="20" @click="handleClick(typeIndex, index)">
                                  <ArrowReplyAll16Filled />
                                </n-icon>
                              </template>
                              返回基本信息
                            </n-tooltip>
                          </n-form-item-gi>
                        </n-grid>
                      </n-form>
                    </n-card>
                  </n-modal>
                </n-card>
              </n-dynamic-input>
            </n-card>
          </n-scrollbar>
        </n-form-item-gi>
        <n-form-item-gi :span="24">
          <n-grid :cols="24" :x-gap="20">
            <n-form-item-gi :span="12" label="类型" path="permission_type">
              <n-cascader
                v-model:value="formValue.permission_type"
                placeholder="请选择"
                :options="typeOptions"
                check-strategy="child"
                remote
                :on-load="handleLoad"
              />
            </n-form-item-gi>
            <n-form-item-gi :span="12" label="使用描述" path="description">
              <n-input v-model:value="formValue.description" placeholder="输入使用描述" />
            </n-form-item-gi>
          </n-grid>
        </n-form-item-gi>
      </n-grid>
    </n-form>
  </n-scrollbar>
</template>

<script>
import { onMounted, onUnmounted, defineComponent } from 'vue';
import createBatchForm from '@/views/vmachine/modules/createBatchForm.js';
import selectMachine from '@/components/machine/selectMachine.vue';
import extendForm from '@/views/versionManagement/product/modules/createForm.js';
import { ExpandSharp } from '@vicons/ionicons5';
import {
  ArrowReplyAll16Filled,
  ArrowCircleUp20Regular,
  ArrowCircleDown20Regular,
} from '@vicons/fluent';
export default defineComponent({
  components: {
    selectMachine,
    ExpandSharp,
    ArrowReplyAll16Filled,
    ArrowCircleUp20Regular,
    ArrowCircleDown20Regular,
  },
  setup(props, context) {
    onMounted(() => {
      createBatchForm.getProductOptions();
    });

    createBatchForm.activeMethodWatcher();
    createBatchForm.activeProductWatcher();
    createBatchForm.activeVersionWatcher();

    onUnmounted(() => {
      createBatchForm.clean();
    });

    return {
      ...createBatchForm,
      typeOptions: extendForm.typeOptions,
      handleLoad: extendForm.handleLoad,
      handlePropsButtonClick: () => createBatchForm.validateFormData(context),
    };
  },
});
</script>

<style lang="less">
.batch-form {
  .n-dynamic-input .n-dynamic-input-item .n-dynamic-input-item__action {
    position: absolute;
    top: 13px;
    right: 44px;
  }
  .n-base-close {
    position: absolute;
    right: 5px;
    top: 5px;
  }
}
</style>
