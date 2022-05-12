import { ref, h,nextTick } from 'vue';
import { NButton, NIcon, NSpace } from 'naive-ui';
import { CancelRound, CheckCircleFilled } from '@vicons/material';
import { getProduct } from '@/api/get';
import { detail,drawerShow,showList } from './productDetailDrawer';
const tableData = ref([
  {
    creator_id: 9485819,
    description: null,
    group_id: null,
    id: 3,
    name: 'openEuler',
    org_id: 1,
    permission_type: 'public',
    version: '20',
  },
]);
const tableLoading = ref(false);
function getTableData () {
  tableLoading.value = true;
  getProduct().then(res => {
    tableData.value = res.data || [];
    tableLoading.value = false;
  }).catch(() => {
    tableLoading.value = false;
  });
}
function renderBtn (text, action, row, type = 'text') {
  return h(NButton, {
    text: type === 'text',
    onClick: () => action(row),
  }, text);
}
function editRow (row) {
  console.log(row);
}
function reportRow (row) {
  console.log(row);
}
function deleteRow (row) {
  console.log(row);
}
const columns = [
  {
    key: 'name',
    title: '产品',
    align: 'center'
  },
  {
    key: 'version',
    align: 'center',
    title: '版本'
  },
  {
    key: 'start_time',
    align: 'center',
    title: '开始时间'
  },
  {
    key: 'end_time',
    align: 'center',
    title: '结束时间'
  },
  {
    key: 'public_time',
    align: 'center',
    title: '发布时间'
  },
  {
    key: 'bequeath',
    align: 'center',
    title: '遗留解决'
  },
  {
    key: 'serious',
    align: 'center',
    title: '严重>80%',
    render () {
      return h(NIcon, { color: 'red',size:24 }, {
        default: () => h(CancelRound)
      });
    }
  },
  {
    key: 'serious',
    align: 'center',
    title: '版本100%',
    render () {
      return h(NIcon, { color: 'green', size: 24 }, {
        default: () => h(CheckCircleFilled)
      });
    }
  },
  {
    title: '操作',
    align: 'center',
    render (row) {
      return h(NSpace, {
        style: 'justify-content: center'
      }, [
        renderBtn('编辑', editRow, row),
        renderBtn('删除', deleteRow, row),
        renderBtn('报告', reportRow, row),
      ]);
    }
  }
];
function rowProps (row) {
  return {
    style:'cursor:pointer',
    onClick: () => {
      detail.value = row;
      drawerShow.value = true;
      nextTick(() => {
        showList.value = false;
      });
    }
  };
}
export {
  tableData,
  columns,
  tableLoading,
  rowProps,
  getTableData
};
