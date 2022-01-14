<template>
  <n-input-group style="margin: 10px 0">
    <n-input
      v-model:value="filterValue.name"
      :style="{ width: '18%' }"
      round
      placeholder="测试套"
      @change="getData"
    />
    <n-input
      v-model:value="filterValue.machine_num"
      :style="{ width: '18%' }"
      round
      placeholder="节点数"
      @change="getData"
    />
    <n-select
      v-model:value="filterValue.machine_type"
      size="large"
      @update:value="getData"
      :style="{ width: '18%' }"
      placeholder="节点类型"
      :options="[
        { label: '虚拟机', value: 'kvm' },
        { label: '物理机', value: 'physical' },
      ]"
      clearable
    />
    <n-input
      v-model:value="filterValue.remark"
      :style="{ width: '18%' }"
      round
      placeholder="备注"
      @change="getData"
    />
    <n-input
      v-model:value="filterValue.owner"
      @change="getData"
      :style="{ width: '18%' }"
      round
      placeholder="责任人"
    />
    <clear-input @clearAll="clearAll" />
  </n-input-group>
  <modal-card
    :initY="100"
    :initX="300"
    title="修改测试套"
    ref="putModalRef"
    @validate="() => putFormRef.put()"
  >
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
import ClearInput from '@/components/CRUD/ClearInput.vue';
const baseColumns = [
  {
    title: '测试套',
    key: 'name',
    align: 'center',
  },
  {
    title: '节点数',
    key: 'machine_num',
    align: 'center',
  },
  {
    title: '节点类型',
    key: 'machine_type',
    align: 'center',
  },
  {
    title: '备注',
    key: 'remark',
    align: 'center',
  },
  {
    title: '责任人',
    key: 'owner',
    align: 'center',
  },
];
function createBtn(type, icon, text, clickFn, row) {
  return renderTooltip(
    h(
      NButton,
      {
        size: 'medium',
        type,
        circle: true,
        onClick: () => clickFn(row),
      },
      h(NIcon, { size: '20' }, h(icon))
    ),
    text
  );
}
export default {
  components: { ClearInput, ...Common, testsuiteCreate },
  methods: {
    getData() {
      this.loading = true;
      this.$axios.get('/v1/suite', this.filterValue).then((res) => {
        this.data = res;
        this.loading = false;
      });
    },
    clearAll() {
      this.filterValue = {
        name: '',
        machine_num: '',
        machine_type: null,
        remark: '',
        owner: '',
      };
      this.getData();
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
        },
      };
    },
  },
  mounted() {
    this.getData();
    this.setPagination();
  },
  setup() {
    const filterValue = ref({
      name: '',
      machine_num: '',
      machine_type: null,
      remark: '',
      owner: '',
    });
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
              align: 'cemter',
            },
            [createBtn('warning', Construct, '修改', editSuite, row)]
          );
        },
      },
    ];
    return {
      columns,
      data,
      pagination: ref(),
      filterValue,
      loading: ref(false),
      putModalRef,
      suiteInfo,
      putFormRef: ref(null),
    };
  },
};
</script>
