import { ref, computed } from 'vue';
import store from '@/store';

const totalData = ref([]);
const loading= ref(true);
const expandedRowKeys = ref([]);

const handleCheck = (rowKeys) => {
  store.commit('selected/setSelectedData', rowKeys);
};
const handleExpand = (rowKeys) => {
  expandedRowKeys.value = rowKeys;
};


const sortQuery = (order = 'ascend') => {
  const copiedData = totalData.value.map((v) => v);
  const orderedData =
    // eslint-disable-next-line no-nested-ternary
    order === 'ascend'
      ? copiedData.sort((rowA, rowB) =>
        rowA.end_time.localeCompare(rowB.end_time)
      )
      : order === 'descend'
        ? copiedData.sort((rowA, rowB) =>
          rowB.end_time.localeCompare(rowA.end_time)
        )
        : copiedData;

  return orderedData;
};

const sorterChange = (sorter, columns) => {
  if (!sorter || sorter.columnKey === 'end_time') {
    const nextData = sortQuery(!sorter ? false : sorter.order);
    columns.value.filter((item) => item.key === 'end_time')[0].sortOrder =
      !sorter ? false : sorter.order;
    totalData.value = nextData;
  }
};

const getFilter = (item, filter) => {
  if (item && filter) {
    return item.toLowerCase().includes(filter.toLowerCase());
  } else if ((!item && !filter) || (item && !filter)) {
    return true;
  }
  return false;
};

const data = computed(() => {
  const filter = store.getters.filterVmState;
  return totalData.value.filter(
    (item) => {
      const frameFilter = getFilter(item.frame, filter.frame);
      const descriptionFilter = getFilter(item.description, filter.description);
      const ipFilter = getFilter(item.ip, filter.ip);
      const hostIpFilter = getFilter(item.host_ip, filter.host_ip);

      return item.name.toLowerCase().includes(filter.name.toLowerCase()) &&
      frameFilter &&
      ipFilter &&
      hostIpFilter &&
      descriptionFilter;
    }
  );
});

export default {
  totalData,
  data,
  loading,
  handleCheck,
  handleExpand,
  sorterChange,
};
