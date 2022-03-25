<template>
  <n-card hoverable>
    <n-grid :cols="24" :x-gap="12">
      <n-gi :span="15">
        <h3>{{ total }} issues in total</h3>
      </n-gi>
      <!-- <n-gi :span="6">
        <n-input
          v-model:value="title"
          placeholder="请输入Issue标题"
          @change="searchIssue"
          round
          clearable
        />
      </n-gi>
      <n-gi :span="3">
        <n-input
          v-model:value="assignee"
          placeholder="请输入责任人"
          @change="searchIssue"
          round
          clearable
        />
      </n-gi> -->
      <n-gi :span="6"></n-gi>
      <n-gi :span="3">
        <n-select
          v-model:value="stateType"
          :options="issueTypeOpts"
          @update:value="changeState"
          round
          placeholder="请选择"
        />
      </n-gi>
    </n-grid>
    <n-data-table
      ref="table"
      size="small"
      :bordered="false"
      :loading="loading"
      :columns="columns"
      :data="rawData"
      :row-props="rowProps"
      :row-key="(row) => row.id"
      :pagination="pagination"
      remote
      @update:page="changePage"
    />
  </n-card>
</template>

<script>
import { ref, defineComponent } from 'vue';
import issuesColumns from '@/views/milestone/modules/issueTableColumns.js';
// import milestoneIssuesAjax from '@/views/milestone/modules/milestoneIssuesAjax.js';
import { getIssueType, getIssue } from '@/api/get';

export default defineComponent({
  props: {
    form: Object,
  },
  mounted() {
    this.getIssueStateType();
  },
  methods: {
    searchIssue() {
      this.changePage(this.pagination.page);
    },
    changeState(state) {
      this.stateType = state;
      this.getData();
    },
    changePage(page) {
      this.pagination.page = page;
      this.getData();
    },
    getData() {
      this.loading = true;
      getIssue({
        page: this.pagination.page,
        per_page: this.pagination.pageSize,
        milestone_id: this.form.id,
        issue_type_id: this.stateType
      })
        .then((res) => {
          const resData = JSON.parse(res.data);
          this.rawData = resData.data;
          this.total = resData.total_count;
          this.loading = false;
          this.pagination.pageCount = Math.ceil(Number(this.total) / this.pagination.pageSize) || 1;
        })
        .catch((err) => {
          if (err.data.validation_error) {
            window.$message.error(err.data.validation_error.body_params[0].msg);
          } else {
            window.$message.error('发生未知错误，获取数据失败');
          }
          this.loading = false;
        });
    },
    getIssueStateType() {
      getIssueType().then(res => {
        this.issueTypeOpts = JSON.parse(res.data).data.map(item => ({ label: item.title, value: String(item.id) }));
        const defect = this.issueTypeOpts.find(item => item.label === '缺陷');
        if (defect) {
          this.stateType = defect.value;
          this.getData();
        } else {
          window.$message?.info('当前组织企业仓的任务类型不存在"缺陷",请手动选择要查询的任务类型');
        }
      });
    }
  },
  setup() {
    const rawData = ref([]);
    const issueTypeOpts = ref([]);
    const loading = ref(false);
    const columns = issuesColumns;
    const total = ref(0);
    const title = ref(null);
    const assignee = ref(null);
    const pagination = ref({
      pageSize: 10,
      page: 1,
      pageCount: 1
    });
    // onMounted(() => {
    //   milestoneIssuesAjax.getData(rawData, loading, total, props, pagination.value);
    // });
    // function changePage(page) {
    //   pagination.value.page = page;
    //   milestoneIssuesAjax.getData(rawData, loading, total, props, pagination.value);
    // }

    return {
      stateType: ref(null),
      rawData,
      loading,
      columns,
      issueTypeOpts,
      pagination,
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
