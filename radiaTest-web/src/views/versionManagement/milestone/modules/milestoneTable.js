import { ref } from 'vue';
import store from '@/store';
import { get } from '@/assets/CRUD/read';

const totalData = ref([]);
const rowData = ref({});
const refresh = ref(false);
const active = ref(false);
const showIssueDrawer = ref(false);
const isCheck = ref(false);
const loading = ref(true);
const isUpdating = ref(false);
const pagination = ref({ 
  page: 1, 
  pageCount: 1, 
  pageSize: 10,
  showSizePicker: true,
  pageSizes: [5, 10, 20, 50]
});
const filter = ref({
  name: '',
  page_num: pagination.value.page,
  page_size: pagination.value.pageSize,
});

const rowProps = (row) => {
  return {
    style: {
      cursor: 'pointer',
    },
    onClick: () => {
      if (!isUpdating.value && !isCheck.value) {
        rowData.value = row;
        active.value = true;
      }
      isCheck.value = false;
      isUpdating.value = false;
    },
  };
};

const handleCheck = (rowKeys) => {
  isCheck.value = true;
  store.commit('selected/setSelectedData', rowKeys);
};
function getTableData() {
  get.list('/v2/milestone', totalData, loading, filter.value, pagination);
}
function changePage(page) {
  pagination.value.page = page;
  filter.value.page_num = page;
  getTableData();
}
function changePageSize(pageSize) {
  pagination.value.page = 1;
  pagination.value.pageSize = pageSize;
  getTableData();
}

export default {
  filter,
  totalData,
  rowData,
  refresh,
  active,
  isCheck,
  loading,
  rowProps,
  handleCheck,
  isUpdating,
  showIssueDrawer,
  pagination,
  changePage,
  changePageSize,
  getTableData,
};
