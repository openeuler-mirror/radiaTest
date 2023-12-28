<template>
  <n-grid :cols="24" y-gap="20">
    <n-gi :span="24">
      <div style="font-size: 30px; font-weight: 600">{{ data.length }} 个任务{{ suffix }}</div>
    </n-gi>
    <n-gi :span="16">
      <label style="font-size: 18px; display: inline-block">
        每页
        <n-select
          :default-value="5"
          :options="[
            { label: '5', value: 5 },
            { label: '10', value: 10 },
            { label: '20', value: 20 },
            { label: '50', value: 50 },
          ]"
          @update:value="handleUpdatePage"
          style="display: inline-block; width: 80px"
          size="small"
          clearable
        />
        个任务
      </label>
    </n-gi>
    <n-gi :span="8">
      <n-input
        v-model:value="searchValue"
        placeholder="搜索任务名......"
        size="large"
        style="width: 100%"
        round
      />
    </n-gi>
    <n-gi :span="24" ref="tableParent">
      <n-data-table
        ref="tableRef"
        size="medium"
        :columns="columns"
        :data="data"
        :row-key="(row) => row.id"
        :pagination="pagination"
        @update:page="pageChange"
        remote
        :row-props="rowProps"
        :scroll-x="tableWidth"
        :indent="20"
        :key="type"
      />
    </n-gi>
  </n-grid>
</template>

<script>
import { ref, watch, defineComponent } from 'vue';
import { getChildrenJob, getJob } from '@/api/get';
import { unkonwnErrorMsg } from '@/assets/utils/description';
import { jobsCard } from '@/views/testCenter/job/modules';

export default defineComponent({
  props: {
    type: {
      default: 'execute',
      type: String,
    },
    total: Number,
  },
  mounted() {
    const tableBoxWidth = this.$refs.tableParent.$el.clientWidth;
    this.tableWidth = tableBoxWidth >= 1600 ? tableBoxWidth : 1600;
    this.getData();
  },
  methods: {
    formatTime(time) {
      return time
        ? new Date(time).toLocaleString('zh-CN', { hourCycle: 'h23' }).replace(/\//g, '-')
        : 0;
    },
    handleUpdatePage(value) {
      this.pagination.pageSize = value || 5;
      this.getData();
    },

    getData() {
      const params = {
        page_size: this.pagination.pageSize,
        page_num: this.pagination.page,
        sorted_by: 'end_time',
      };
      if (this.type === 'wait') {
        params.status = 'PENDING';
      } else if (this.type === 'finish') {
        params.status = 'DONE';
      }
      getJob(params)
        .then((res) => {
          res.data?.items?.forEach((item) => {
            if (item.multiple) {
              item.children = [{}];
            }
            item.create_time = this.formatTime(item.create_time);
            item.end_time = this.formatTime(item.end_time);
            item.start_time = this.formatTime(item.start_time);
          });
          this.data = res.data?.items || [];
          this.pagination.pageCount = res.data.pages;
        })
        .catch((err) => window.$message?.error(err.data.error_msg || unkonwnErrorMsg));
    },
    pageChange(page) {
      this.pagination.page = page;
      this.getData();
    },
    rowProps(rowData) {
      return {
        onClick: (e) => {
          if (rowData.multiple) {
            const iconNode = ['path', 'svg'];
            if (iconNode.includes(e.target.nodeName.toLocaleLowerCase())) {
              if (!rowData.children[0]?.id) {
                getChildrenJob(rowData.id).then((res) => {
                  res.data?.forEach((item) => {
                    item.start_time
                      ? (item.start_time = new Date(item.start_time)
                          .toLocaleString('zh-CN', { hourCycle: 'h23' })
                          .replace(/\//g, '-'))
                      : 0;
                    item.end_time
                      ? (item.end_time = new Date(item.end_time)
                          .toLocaleString('zh-CN', { hourCycle: 'h23' })
                          .replace(/\//g, '-'))
                      : 0;
                    item.create_time = new Date(item.create_time).getTime();
                  });
                  rowData.children = res.data || [{}];
                });
              }
            }
          }
        },
      };
    },
  },
  setup(props) {
    const suffix = ref('');
    const tableWidth = ref(1600);

    const pagination = ref({
      page: 1,
      pageCount: 1,
      pageSize: 5,
    });
    const columns = ref([]);
    const searchValue = ref('');

    jobsCard.initColumns(columns, props.type);
    jobsCard.initSuffix(suffix, props.type);

    watch(props, jobsCard.initColumns(columns, props.type), { deep: true });

    const data = ref([]);

    return {
      data,
      suffix,
      columns,
      pagination,
      tableWidth,
      searchValue,
    };
  },
});
</script>
