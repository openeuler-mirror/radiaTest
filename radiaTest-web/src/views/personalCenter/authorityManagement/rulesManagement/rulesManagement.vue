<template>
  <div>
    <div
      style="
        margin-bottom: 20px;
        display: flex;
        justify-content: space-between;
        align-items: center;
      "
    >
      <h3>规则</h3>
      <n-button type="primary" @click="createRule">
        <template #icon>
          <n-icon>
            <Add />
          </n-icon>
        </template>
        创建规则
      </n-button>
    </div>
    <rule-form
      :type="formType"
      ref="createRef"
      :formData="editData"
      @submitform="submitForm"
    />
    <table-filter :filters="filters" @filterchange="filterChange" />
    <n-data-table :columns="columns" :data="data" :pagination="pagination" />
  </div>
</template>
<script>
import { Add } from '@vicons/ionicons5';
import { modules } from './modules';
import ruleForm from '@/components/form/ruleForm.vue';
import tableFilter from '@/components/filter/tableFilter.vue';
export default {
  components: {
    Add,
    ruleForm,
    tableFilter
  },
  setup() {
    modules.getRules();
    return {
      ...modules
    };
  }
};
</script>
