import { ref, computed } from 'vue';
import store from '@/store';

const totalData = ref([]);
const rowData = ref({});
const refresh = ref(false);
const active= ref(false);
const isCheck= ref(false);
const expandedRowKeys= ref([]);
const loading= ref(true);
const isUpdating = ref(false);

const rowProps= (row) => {
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

const handleFilter = (item, filter) => {
  if (!filter) {
    return true;
  }
  return item.toLowerCase().includes(filter.toLowerCase());  
};

const data = computed(() => {
  const filter = store.getters.filterProductState;
  return totalData.value.filter(
    (item) =>
      handleFilter(item.name, filter.name) &&
      handleFilter(item.version, filter.version) &&
      handleFilter(item.description, filter.description)
  );
});

const handleCheck = (rowKeys) => {
  isCheck.value = true;
  store.commit('selected/setSelectedData', rowKeys);
};

export default {
  data,
  totalData,
  rowData,
  refresh,
  active,
  isCheck,
  expandedRowKeys,
  loading,
  rowProps,
  handleCheck,
  isUpdating,
};
