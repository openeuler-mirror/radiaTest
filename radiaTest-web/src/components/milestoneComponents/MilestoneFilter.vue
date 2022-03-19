<template>
  <n-input
    size="large"
    v-model:value="filter.name"
    round
    @change="searchMilestone"
    placeholder="搜索里程碑名..."
    clearable
  />
</template>

<script>
import { defineComponent } from 'vue';
import milestoneTable from '@/views/milestone/modules/milestoneTable';
import { get } from '@/assets/CRUD/read';

export default defineComponent({
  methods: {
    searchMilestone() {
      get.list('/v2/milestone', milestoneTable.totalData, milestoneTable.loading, milestoneTable.filter.value);
    }
  },
  setup() {
    return {
      ...milestoneTable
    };
  },
});
</script>

<style scoped></style>
