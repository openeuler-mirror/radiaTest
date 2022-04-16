import store from '@/store/index';
import router from '@/router/index';
import axios from '@/axios';
import { formatTime } from '@/assets/utils/dateFormatUtils.js';
import { storage } from '@/assets/utils/storageUtils';
import { ref, toRef, h } from 'vue';
import { NButton } from 'naive-ui';
import { editTask } from '../task/modules/taskDetail.js';
import { getGroup } from '@/api/get';

const menuSelect = ref(null); // 当前页面索引值
const isTask = ref(true); // 是否是任务页面
const kanban = toRef(store.state.taskManage, 'kanban'); // 看板视图、表格视图切换
const active = ref(false); // 显示筛选
const formRef = ref(null); // 筛选表单名称
const taskTypeOptions = ref([]); // 任务类型
const originators = ref([]); // 创建者
const executors = ref([]); // 执行者
const participants = ref([]); // 协助人
const statusOptions = ref([]); // 任务状态
const recycleBinTaskTable = ref(null); // 回收站表格名称
const recycleBinTaskLoading = ref(false); // 回收站表格加载状态
const showRecycleBinModal = ref(false); // 显示回收站表格

// 回收站表格分页
const recycleBinTaskPagination = ref({
  page: 1, // 受控模式下的当前页
  pageCount: 1, // 总页数
  pageSize: 10, // 受控模式下的分页大小
});

// 确认弹框
function warning (title, content, cb) {
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
const recycleBinTaskData = ref([]);

// 任务类型英转中
function typeNameTrans (type) {
  switch (type) {
    case 'PERSON':
      return '个人任务';
    case 'GROUP':
      return '团队任务';
    case 'ORGANIZATION':
      return '组织任务';
    case 'VERSION':
      return '版本任务';
    default:
      return '';
  }
}

// 查询回收站任务
function query (page) {
  axios
    .get('/v1/tasks/recycle_bin', { page_num: page })
    .then((res) => {
      recycleBinTaskLoading.value = false;
      if (res.data.items) {
        recycleBinTaskData.value = res.data.items.map((task, index) => {
          return {
            key: index,
            id: task.id,
            name: task.title,
            type: typeNameTrans(task.type),
            originator: task.originator.gitee_name,
            deleteTime: formatTime(task.update_time, 'yyyy-MM-dd hh:mm:ss'),
          };
        });
        recycleBinTaskPagination.value.pageCount = res.data.pages;
        recycleBinTaskPagination.value.pageSize = res.data.page_size;
        recycleBinTaskPagination.value.page = res.data.current_page;
      } else {
        recycleBinTaskData.value = [];
      }
    })
    .catch((err) => {
      recycleBinTaskLoading.value = false;
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

// 回收站表格列数据
const recycleBinTaskColumns = [
  {
    title: '名称',
    align: 'center',
    key: 'name',
  },
  {
    title: '类型',
    key: 'type',
    align: 'center',
  },
  {
    title: '创建人',
    align: 'center',
    key: 'originator',
  },
  {
    title: '删除时间',
    align: 'center',
    key: 'deleteTime',
  },
  {
    title: '操作',
    align: 'center',
    render (row) {
      return [
        h(
          NButton,
          {
            type: 'primary',
            text: true,
            style: 'margin-right:10px;',
            onClick: () => {
              warning('恢复任务', '您确定要恢复此任务吗？', () => {
                editTask(row.id, { is_delete: false });
                query(recycleBinTaskPagination.value.page);
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
              warning('彻底删除任务', '您确定要彻底删除此任务吗？', () => {
                axios
                  .delete(`/v1/tasks/${row.id}`)
                  .then(() => {
                    query(recycleBinTaskPagination.value.page);
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

// 筛选表单数据
const model = ref({
  title: null,
  executor_id: null,
  originator: null,
  participant_id: null,
  status_id: null,
  start_time: null,
  deadline: null,
  type: null,
});

// 筛选表单验证规则
const rules = ref({});

// tab名称
const menu = ref([
  {
    id: 0,
    text: '任务',
    name: 'task',
  },
  {
    id: 1,
    text: '可视化',
    name: 'report',
  },
  {
    id: 2,
    text: '分配模板',
    name: 'distribution',
  },
]);

// 初始化
function initCondition () {
  const allRequest = [
    axios.get('/v1/task/status'),
    axios.get(`/v1/org/${storage.getValue('orgId')}/users`, {
      page_num: 1,
      page_size: 9999,
    }),
    getGroup({ page_size: 99999, page_num: 1 }),
  ];
  Promise.allSettled(allRequest).then((responses) => {
    if (responses[0].value?.data) {
      statusOptions.value = [];
      responses[0].value.data?.forEach((item) => {
        statusOptions.value.push({
          label: item.name,
          value: item.id,
        });
      });
    }
    if (responses[1].value?.data) {
      executors.value = [];
      participants.value = [];
      originators.value = [];
      responses[1].value.data?.items?.forEach((item) => {
        const option = {
          label: item.gitee_name,
          value: item.gitee_id,
        };
        originators.value.push(option);
        executors.value.push(option);
        participants.value.push(option);
      });
    }
    if (responses[2].value?.data) {
      responses[2].value.data?.items?.forEach((item) => {
        const option = {
          label: item.name,
          value: item.id,
        };
        executors.value.push(option);
        participants.value.push(option);
      });
    }
  });
}

// 筛选
function handleValidateButtonClick (e) {
  e.preventDefault();
  formRef.value.validate((errors) => {
    if (!errors) {
      const formData = JSON.parse(JSON.stringify(model.value));
      if (model.value.deadline > 0) {
        formData.deadline = formatTime(
          model.value.deadline,
          'yyyy-MM-dd hh:mm:ss'
        );
      }
      if (model.value.start_time > 0) {
        formData.start_time = formatTime(
          model.value.start_time,
          'yyyy-MM-dd hh:mm:ss'
        );
      }
      document.dispatchEvent(
        new CustomEvent('searchTask', {
          detail: formData,
        })
      );
      active.value = false;
    } else {
      window.$message?.error('验证失败');
    }
  });
}

// 页面切换
function menuClick (item, index) {
  menuSelect.value = index;
  router.push(`/home/tm/${item.name}`);
  item.name === 'task' ? (isTask.value = true) : (isTask.value = false);
}

// 视图切换
function toggleView () {
  store.commit('taskManage/toggleView');
}

// 显示筛选框
function screen () {
  active.value = true;
}

// 重置筛选条件
function clearCondition (e) {
  model.value = {
    title: null,
    executor_id: null,
    originator: null,
    participant_id: null,
    status_id: null,
    start_time: null,
    deadline: null,
    type: null,
  };
  handleValidateButtonClick(e);
}

// 显示回收站按钮
function showRecycleBin () {
  showRecycleBinModal.value = true;
  recycleBinTaskLoading.value = true;
  query(1);
}

// 回收站表格页数变动
function recycleBinTablePageChange (currentPage) {
  if (!recycleBinTaskLoading.value) {
    recycleBinTaskLoading.value = true;
    query(currentPage);
  }
}

export {
  menuSelect,
  isTask,
  kanban,
  active,
  formRef,
  taskTypeOptions,
  originators,
  executors,
  participants,
  statusOptions,
  model,
  rules,
  menu,
  initCondition,
  handleValidateButtonClick,
  menuClick,
  toggleView,
  screen,
  clearCondition,
  recycleBinTaskTable,
  recycleBinTaskLoading,
  recycleBinTaskColumns,
  recycleBinTaskData,
  showRecycleBinModal,
  showRecycleBin,
  recycleBinTaskPagination,
  recycleBinTablePageChange,
};
