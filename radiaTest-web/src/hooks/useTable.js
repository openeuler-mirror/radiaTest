import axios from '@/axios';
import { storage } from '@/assets/utils/storageUtils';

export const useTable = (url, params, tableData, pagination, loading, once) => {
  const getTableData = () => {
    loading.value = true;
    let addedOrgData = {};
    if (params) {
      addedOrgData = params;
      addedOrgData.org_id = storage.getLocalValue('unLoginOrgId').id;
    } else {
      addedOrgData.org_id = storage.getLocalValue('unLoginOrgId').id;
    }
    axios.get(url, addedOrgData).then((res) => {
      loading.value = false;
      pagination.value.pageCount = res.data.pages;
      tableData.value = res.data?.items;
    });
  };
  let stop = () => { };
  if (once) {
    getTableData();
  } else {
    stop = watchEffect(getTableData);
  }
  return stop;
};
