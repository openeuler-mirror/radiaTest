import { ref, computed } from 'vue';
import store from '@/store';

const totalData = ref([]);
const rowData = ref({});
const refresh = ref(false);
const active = ref(false);
const showDetailDrawer = ref(false);
const isDelete = ref(false);
const loading = ref(true);
const isUpdating = ref(false);

const rowProps = (row) => {
  return {
    style: {
      cursor: 'pointer'
    },
    onClick: () => {
      if (!isUpdating.value && !isDelete.value) {
        rowData.value = row;
        active.value = true;
      }
      isDelete.value = false;
      isUpdating.value = false;
    }
  };
};

const getFilter = (item, filter) => {
  if (item && filter) {
    return item
      .toString()
      .toLowerCase()
      .includes(filter.toLowerCase());
  } else if ((!item && !filter) || (item && !filter)) {
    return true;
  }
  return false;
};

const data = computed(() => {
  const filter = store.getters.filterCaseState;
  return totalData.value.items && totalData.value.items.filter((item) => {
    const suiteFilter = getFilter(item.suite, filter.suite);
    const nameFilter = getFilter(item.name, filter.name);
    const machineNumFilter = getFilter(item.machine_num, filter.machine_num);
    const machineTypeFilter = getFilter(item.machine_type, filter.machine_type);
    const testLevelFilter = getFilter(item.test_level, filter.test_level);
    const testTypeFilter = getFilter(item.test_type, filter.test_type);
    const automaticFilter = item.automatic === filter.automatic || filter.automatic === null;
    const remarkFilter = getFilter(item.remark, filter.remark);
    const ownerFilter = getFilter(item.owner, filter.owner);

    return (
      suiteFilter && nameFilter && testLevelFilter && testTypeFilter && machineNumFilter && machineTypeFilter && automaticFilter && remarkFilter && ownerFilter
    );
  });
});
const pageCounts = computed(() => totalData.value.pages);
export default {
  data,
  totalData,
  rowData,
  refresh,
  active,
  isDelete,
  loading,
  rowProps,
  isUpdating,
  showDetailDrawer,
  pageCounts,
};
