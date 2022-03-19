<template>
  <div class="form-box-container">
    <div style="flex: 3">
      <n-form
        inline
        :label-width="80"
        :model="formValue"
        :rules="rules"
        size="medium"
        ref="formRef"
      >
        <n-grid :cols="24">
          <n-form-item-gi :span="23" label="架构" path="frame">
            <n-select
              filterable
              v-model:value="formValue.frame"
              placeholder="请选择架构"
              :options="[
                {
                  label: 'aarch64',
                  value: 'aarch64',
                },
                {
                  label: 'x86_64',
                  value: 'x86_64',
                },
              ]"
            />
          </n-form-item-gi>
          <n-form-item-gi :span="13" label="选取策略" path="select_mode">
            <n-select
              :options="[
                {
                  label: '全自动选取',
                  value: 'auto',
                },
                {
                  label: '人工干预',
                  value: 'manual',
                },
              ]"
              v-model:value="formValue.select_mode"
              placeholder="选取策略"
            />
          </n-form-item-gi>
          <n-form-item-gi :span="10" label="是否严格模式" path="strict_mode">
            <n-switch
              v-model:value="formValue.strict_mode"
              :disabled="formValue.select_mode === 'auto'"
            >
              <template #checked> 是 </template>
              <template #unchecked> 否 </template>
            </n-switch>
          </n-form-item-gi>
          <n-gi
            :span="24"
            v-if="formValue.pm_req_num && formValue.select_mode === 'manual'"
          >
            <n-divider> 物理机选取 </n-divider>
          </n-gi>
          <n-form-item-gi
            :span="23"
            label="已选机器"
            path="machine_list"
            v-if="formValue.pm_req_num && formValue.select_mode === 'manual'"
          >
            <n-select
              filterable
              :value="formValue.pmachine_list"
              @update:value="selectmachine('pm', $event)"
              placeholder="请选择机器"
              :options="pmOpt"
              multiple
            >
              <template #arrow>
                {{ formValue.pmachine_list.length }}/{{ formValue.pm_req_num }}
              </template>
            </n-select>
          </n-form-item-gi>
          <n-gi
            :span="24"
            v-if="formValue.vm_req_num && formValue.select_mode === 'manual'"
          >
            <n-divider> 虚拟机选取 </n-divider>
          </n-gi>
          <n-form-item-gi
            :span="23"
            label="已选机器"
            path="machine_list"
            v-if="formValue.vm_req_num && formValue.select_mode === 'manual'"
          >
            <n-select
              filterable
              :value="formValue.vmachine_list"
              @update:value="selectmachine('vm', $event)"
              placeholder="请选择机器"
              :options="vmOpt"
              multiple
            >
              <template #arrow>
                {{ formValue.vmachine_list.length }}/{{ formValue.vm_req_num }}
              </template>
            </n-select>
          </n-form-item-gi>
        </n-grid>
      </n-form>
    </div>
    <div style="flex: 2">
      <div class="list-item">
        <div class="list-label">模板名:</div>
        <div class="list-value">{{ formValue.name }}</div>
      </div>
      <div class="list-item">
        <div class="list-label">描述:</div>
        <div class="list-value">{{ formValue.description }}</div>
      </div>
      <div class="list-item">
        <div class="list-label">权限归属:</div>
        <div class="list-value">
          {{ formValue.owner }}
          <n-tag type="success" style="margin-left: 10px">
            {{ tagOptions[formValue.template_type] }}
          </n-tag>
        </div>
      </div>
      <div class="list-item">
        <div class="list-label">里程碑:</div>
        <div class="list-value">{{ formValue.milestone }}</div>
      </div>
      <expandedCard :data="formValue.cases.map((item) => ({ name: item }))" />
    </div>
  </div>
</template>
<script>
import { formValue, vmOpt, pmOpt, selectmachine } from '@/views/template/modules/execTemplate';
import expandedCard from '@/components/templateComponents/ExpandedCard.vue';
export default {
  props: {
    name: String,
  },
  components: {
    expandedCard
  },
  setup() {
    return {
      formValue,
      tagOptions: {
        personal: '个人'
      },
      selectmachine,
      vmOpt,
      pmOpt,
      rules: []
    };
  }
};
</script>
<style lang="less" scoped>
.form-box-container {
  display: flex;
  width: 1000px;
  .list-item {
    display: flex;
    margin: 15px 10px;
    .list-label {
      width: 80px;
      flex-shrink: 0;
      font-weight: 500;
    }
    .list-value {
      width: 100%;
    }
  }
}
</style>
