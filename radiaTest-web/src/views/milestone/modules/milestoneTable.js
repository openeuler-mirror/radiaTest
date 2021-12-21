import { ref, computed } from 'vue';
import store from '@/store';

const totalData = ref([]);
const rowData = ref({});
const refresh = ref(false);
const active= ref(false);
const showIssueDrawer = ref(false);
const isCheck= ref(false);
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

const data = computed(() => {
  const filterName = store.getters.filterMilestoneState.value;
  return totalData.value.filter(
    (item) =>
      item.name.toLowerCase().includes(filterName.toLowerCase())
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
  loading,
  rowProps,
  handleCheck,
  isUpdating,
  showIssueDrawer,
};
