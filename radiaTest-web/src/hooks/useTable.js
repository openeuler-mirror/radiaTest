import axios from '@/axios';

export const useTable = (url, params, tableData, pagination, loading, once) => {
  const getTableData = () => {
    loading.value = true;
    axios.get(url, params).then((res) => {
      loading.value = false;
      pagination.value.pageCount = res.data.pages;
      tableData.value = res.data?.items;
    });
  };
  let stop = () => {};
  if (once) {
    getTableData();
  } else {
    stop = watchEffect(getTableData);
  }

  onUnmounted(() => {
    stop();
  });
};
