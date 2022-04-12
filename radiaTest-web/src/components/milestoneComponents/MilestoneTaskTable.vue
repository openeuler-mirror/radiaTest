<template>
  <div>
    <div style="display:flex;justify-content:flex-end;margin:10px 0;">
      <n-input
        round
        @change="getData"
        v-model:value="title"
        placeholder="请输入"
        clearable
        style="width:300px"
      />
    </div>
    <n-data-table
      :data="data"
      :loading="loading"
      :pagination="pagination"
      :columns="columns"
    />
  </div>
</template>
<script>
import { getMilestoneTask } from '@/api/get';
function transTaskType(type) {
  switch (type) {
    case 'PERSON':
      return '个人任务';
    case 'GROUP':
      return '团队任务';
    case 'ORGANIZATION':
      return '组织任务';
    case 'VERSION':
      return '版本任务';
    default:
      return '';
  }
}
export default {
  props: ['milestoneId'],
  data() {
    return {
      loading: false,
      title: '',
      pagination: {
        page: 1,
        pageSize: 10,
        pageCount: 1,
      },
      data: [],
      columns: [
        { title: '任务名称', key: 'title', align: 'center' },
        {
          title: '任务类型',
          key: 'type',
          align: 'center',
          render: (row) => transTaskType(row.type),
        },
        { title: '关键词', key: 'keywords', align: 'center' },
        { title: '架构', key: 'frame', align: 'center' },
      ],
    };
  },
  mounted() {
    this.getData();
  },
  methods: {
    getData() {
      this.loading = true;
      getMilestoneTask(this.milestoneId, {
        page_num: this.pagination.page,
        page_size: this.pagination.pageSize,
        title: this.title,
      })
        .then((res) => {
          this.loading = false;
          this.data = res.data?.items || [];
          this.pagination.pageCount = res.data.pages;
        })
        .catch((err) => {
          this.loading = false;
          window.$message?.error(err.data?.error_msg || err.message);
        });
    },
  },
};
</script>
