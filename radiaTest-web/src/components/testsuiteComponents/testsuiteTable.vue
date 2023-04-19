<template>
  <modal-card :initY="100" :initX="300" title="修改测试套" ref="putModalRef" @validate="() => putFormRef.put()">
    <template #form>
      <testsuite-create
        ref="putFormRef"
        :data="suiteInfo"
        @close="
          () => {
            putModalRef.close();
          }
        "
      />
    </template>
  </modal-card>
  <n-data-table
    ref="table"
    size="large"
    :bordered="false"
    :columns="columns"
    :data="data"
    :loading="loading"
    :pagination="pagination"
    :row-key="(row) => row.id"
  />
</template>
<script>
import { h, ref } from 'vue';
import { NIcon, NButton, NSpace } from 'naive-ui';
import { Construct } from '@vicons/ionicons5';
import Common from '@/components/CRUD';
import testsuiteCreate from '@/components/testsuiteComponents/testsuiteCreate.vue';
import { renderTooltip } from '@/assets/render/tooltip';
import { workspace } from '@/assets/config/menu.js';

const baseColumns = [
  {
    title: '测试套',
    key: 'name',
    align: 'center'
  },
  {
    title: '节点数',
    key: 'machine_num',
    align: 'center'
  },
  {
    title: '节点类型',
    key: 'machine_type',
    align: 'center'
  },
  {
    title: '备注',
    key: 'remark',
    align: 'center'
  },
  {
    title: '责任人',
    key: 'owner',
    align: 'center'
  }
];
function createBtn(type, icon, text, clickFn, row) {
  return renderTooltip(
    h(
      NButton,
      {
        size: 'medium',
        type,
        circle: true,
        onClick: () => clickFn(row)
      },
      h(NIcon, { size: '20' }, h(icon))
    ),
    text
  );
}
export default {
  components: { ...Common, testsuiteCreate },
  methods: {
    getData() {
      this.loading = true;
      this.$axios.get(`/v1/ws/${workspace.value}/suite`).then((res) => {
        this.data = res.data;
        this.loading = false;
      });
    },
    setPagination() {
      this.pagination = {
        page: 1,
        showSizePicker: true,
        pageSize: 10,
        pageSizes: [5, 10, 20, 50],
        onChange: (page) => {
          this.pagination.page = page;
        },
        onPageSizeChange: (pageSize) => {
          this.pagination.pageSize = pageSize;
          this.pagination.page = 1;
        }
      };
    }
  },
  mounted() {
    this.getData();
    this.setPagination();
  },
  setup() {
    const suiteInfo = ref();
    const putModalRef = ref(null);
    function editSuite(row) {
      suiteInfo.value = row;
      putModalRef.value.show();
    }
    const data = ref([]);
    const columns = [
      ...baseColumns,
      {
        title: '操作',
        key: 'action',
        align: 'center',
        render: (row) => {
          return h(
            NSpace,
            {
              justify: 'center',
              align: 'cemter'
            },
            [createBtn('warning', Construct, '修改', editSuite, row)]
          );
        }
      }
    ];
    return {
      columns,
      data,
      pagination: ref(),
      loading: ref(false),
      putModalRef,
      suiteInfo,
      putFormRef: ref(null)
    };
  }
};
</script>
