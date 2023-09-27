import { h, ref } from 'vue';
import axios from '@/axios';
import router from '@/router/index';
import { NButton } from 'naive-ui';
import { formatTime } from '@/assets/utils/dateFormatUtils.js';
import { updateAjax } from '@/assets/CRUD/update';
// import { workspace } from '@/assets/config/menu.js';

const menuSelect = ref(0); // 当前页面索引值

const recycleBinCaseTable = ref(null); // 回收站表格名称
const recycleBinCaseLoading = ref(false); // 回收站表格加载状态
const showRecycleBinModal = ref(false); // 显示回收站表格

// 回收站表格分页
const recycleBinCasePagination = ref({
  pageSize: 10,
});

// 确认弹框
function warning(title, content, cb) {
  const d = window.$dialog?.warning({
    title,
    content,
    action: () => {
      const confirmBtn = h(
        NButton,
        {
          type: 'info',
          ghost: true,
          onClick: () => {
            if (cb) {
              cb();
            }
            d.destroy();
          },
        },
        '确定'
      );
      const cancelmBtn = h(
        NButton,
        {
          type: 'error',
          ghost: true,
          onClick: () => {
            d.destroy();
          },
        },
        '取消'
      );
      return [cancelmBtn, confirmBtn];
    },
  });
}

// 回收站表格行数据
const recycleBinCaseData = ref([]);

// 查询回收站
function query() {
  // 需要后端适配
  axios
    .get('/v1/ws/default/case/recycle-bin')
    .then((res) => {
      recycleBinCaseLoading.value = false;
      recycleBinCaseData.value = res.data.map((_case, index) => {
        return {
          key: index,
          id: _case.id,
          suite: _case.suite,
          name: _case.name,
          test_type: _case.test_type,
          test_level: _case.test_level,
          owner: _case.owner,
          deleteTime: formatTime(_case.update_time, 'yyyy-MM-dd hh:mm:ss'),
        };
      });
    })
    .catch((err) => {
      recycleBinCaseLoading.value = false;
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

// 回收站表格列数据
const recycleBinCaseColumns = [
  {
    title: '测试套',
    align: 'center',
    key: 'suite',
  },
  {
    title: '用例名',
    align: 'center',
    key: 'name',
  },
  {
    title: '测试等级',
    align: 'center',
    key: 'test_level',
  },
  {
    title: '测试类型',
    align: 'center',
    key: 'test_type',
  },
  {
    title: '责任人',
    align: 'center',
    key: 'owner',
  },
  {
    title: '删除时间',
    align: 'center',
    key: 'deleteTime',
  },
  {
    title: '操作',
    align: 'center',
    render(row) {
      return [
        h(
          NButton,
          {
            type: 'primary',
            text: true,
            style: 'margin-right:10px;',
            onClick: () => {
              warning('恢复用例', '您确定要恢复此用例吗？', () => {
                updateAjax.putForm(
                  `/v1/case/${row.id}`,
                  ref({ deleted: false })
                );
                query();
              });
            },
          },
          '恢复'
        ),
        h(
          NButton,
          {
            type: 'primary',
            text: true,
            onClick: () => {
              warning('彻底删除用例', '您确定要彻底删除此用例吗？', () => {
                axios
                  .delete(`/v1/case/${row.id}`)
                  .then(() => {
                    query();
                  })
                  .catch((err) => {
                    window.$message?.error(err.data.error_msg || '未知错误');
                  });
              });
            },
          },
          '彻底删除'
        ),
      ];
    },
  },
];

// 页面切换
function menuClick(item, index) {
  menuSelect.value = index;
  router.push({ name: item.name });
}

// tab名称
const menu = ref([
  {
    id: 1,
    text: '用例仓库',
    name: 'folderview',
  },
  {
    id: 2,
    text: '用例评审',
    name: 'caseReview',
  },
  {
    id: 3,
    text: '测试框架',
    name: 'frameWork',
  },
]);

const isTabActive = (name) => {
  if (name !== 'folderview') {
    return router.currentRoute.value.name === name;
  }
  return router.currentRoute.value.fullPath.includes('/tcm/folderview');
};

function showRecycleBin() {
  showRecycleBinModal.value = true;
  recycleBinCaseLoading.value = true;
  query();
}

export default {
  menuClick,
  menu,
  menuSelect,
  recycleBinCaseTable,
  recycleBinCaseLoading,
  showRecycleBinModal,
  recycleBinCasePagination,
  recycleBinCaseData,
  recycleBinCaseColumns,
  isTabActive,
  showRecycleBin,
};
