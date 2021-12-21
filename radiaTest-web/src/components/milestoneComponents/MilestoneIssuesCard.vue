<template>
  <n-card hoverable>
    <n-grid :cols="24" :x-gap="12">
      <n-gi :span="15">
        <h3>{{ total }} issues in total</h3>
      </n-gi>
      <n-gi :span="6">
        <n-input
          v-model:value="title"
          placeholder="请输入Issue标题"
          round
          clearable
        />
      </n-gi>
      <n-gi :span="3">
        <n-input
          v-model:value="assignee"
          placeholder="请输入责任人"
          round
          clearable
        />
      </n-gi>
    </n-grid>
    <n-data-table
      ref="table"
      size="small"
      :bordered="false"
      :loading="loading"
      :columns="columns"
      :data="data"
      :row-props="rowProps"
      :row-key="(row) => row.id"
      :pagination="pagination"
    />
  </n-card>
</template>

<script>
import { ref, computed, onMounted, defineComponent } from 'vue';
import issuesColumns from '@/views/milestone/modules/issueTableColumns.js';
import milestoneIssuesAjax from '@/views/milestone/modules/milestoneIssuesAjax.js';

export default defineComponent({
  props: {
    form: Object,
  },
  setup(props) {
    const rawData = ref([]);
    const loading = ref(false);
    const columns = issuesColumns;
    const total = ref(0);
    const title = ref(null);
    const assignee = ref(null);
    const data = computed(() =>
      rawData.value.filter((item) => {
        return (
          (!title.value || item.title.includes(title.value)) &&
          (!assignee.value ||
            (item.assignee && item.assignee.name.includes(assignee.value)))
        );
      })
    );

    onMounted(() => {
      milestoneIssuesAjax.getData(rawData, loading, total, props);
    });

    return {
      data,
      loading,
      columns,
      pagination: { pageSize: 10 },
      total,
      title,
      assignee,
      rowProps: (row) => {
        return {
          style: {
            cursor: 'pointer',
          },
          onClick: () => {
            window.open(row.html_url);
          },
        };
      },
    };
  },
});
</script>

<style>
.issueState {
  width: 5%;
}
.issueNumber {
  width: 5%;
}
.issueTitle {
  width: 42%;
}
</style>
