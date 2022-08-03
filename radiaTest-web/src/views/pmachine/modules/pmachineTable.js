import { ref, computed } from 'vue';
import store from '@/store';
import { ColumnEndtime } from './pmachineTableColumns';

const totalData = ref([]);
const rowData = ref({});
const refresh = ref(false);
const loading = ref(false);
const expandedRowKeys = ref([]);

const handleCheck = (rowKeys) => {
  store.commit('selected/setSelectedData', rowKeys);
};
const handleExpand = (rowKeys) => {
  expandedRowKeys.value = rowKeys;
};

const sortQuery = (order = 'ascend') => {
  const copiedData = totalData.value.map((v) => v);
  let orderedData;
  if (order === 'ascend') {
    orderedData = copiedData.sort((rowA, rowB) => rowA.end_time.localeCompare(rowB.end_time));
  } else if (order === 'descend') {
    orderedData = copiedData.sort((rowA, rowB) => rowB.end_time.localeCompare(rowA.end_time));
  } else {
    orderedData = copiedData;
  }

  return orderedData;
};

const handleSorterChange = (sorter) => {
  if (!sorter || sorter.columnKey === 'end_time') {
    const nextData = sortQuery(!sorter ? false : sorter.order);
    ColumnEndtime.value.sortOrder = !sorter ? false : sorter.order;
    totalData.value = nextData;
  }
};

const getFilter = (item, filter) => {
  if (item && filter) {
    return item
      .toString()
      .toLowerCase()
      .includes(filter.toString().toLowerCase());
  } else if ((!item && !filter) || (item && !filter)) {
    return true;
  }
  return false;
};

const data = computed(() => {
  const filter = store.getters.filterPmState;
  return totalData.value.filter((item) => {
    const macFilter = getFilter(item.mac, filter.mac);
    const frameFilter = getFilter(item.frame, filter.frame);
    const occupierFilter = getFilter(item.occupier, filter.occupier);
    const ipFilter = getFilter(item.ip, filter.ip);
    const bmcIpFilter = getFilter(item.bmc_ip, filter.bmc_ip);
    const stateFilter = getFilter(item.state, filter.state);
    const descriptionFilter = getFilter(item.description, filter.description);

    return macFilter && frameFilter && ipFilter && bmcIpFilter && occupierFilter && stateFilter && descriptionFilter;
  });
});

export default {
  totalData,
  data,
  rowData,
  refresh,
  loading,
  handleCheck,
  handleExpand,
  handleSorterChange
};
