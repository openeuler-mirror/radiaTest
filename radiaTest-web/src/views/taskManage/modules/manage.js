import store from '@/store/index';
import router from '@/router/index';
import axios from '@/axios';
import { formatTime } from '@/assets/utils/dateFormatUtils.js';
import { storage } from '@/assets/utils/storageUtils';
import { NButton } from 'naive-ui';
import { editTask } from '../task/modules/taskDetail.js';
import { getGroup } from '@/api/get';

const menuSelect = ref(null); // 当前页面索引值
const isTask = ref(true); // 是否是任务看板页面
const backable = ref(false); // 是否可以返回任务看板
const kanban = toRef(store.state.taskManage, 'kanban'); // 泳道视图、甘特视图切换
const originators = ref([]); // 创建者
const executors = ref([]); // 执行者
const participants = ref([]); // 协助人
const statusOptions = ref([]); // 任务状态
const milestones = ref([]); // 里程碑列表
const recycleBinTaskTable = ref(null); // 回收站表格名称
const recycleBinTaskLoading = ref(false); // 回收站表格加载状态
const showRecycleBinModal = ref(false); // 显示回收站表格
const isDesign = ref(false); // 是否是测试设计页面
const isDesignTemplate = ref(false); // 是否是测试设计模板页

// 回收站表格分页
const recycleBinTaskPagination = ref({
  page: 1, // 受控模式下的当前页
  pageCount: 1, // 总页数
  pageSize: 10 // 受控模式下的分页大小
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
          }
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
          }
        },
        '取消'
      );
      return [cancelmBtn, confirmBtn];
    }
  });
}

// 回收站表格行数据
const recycleBinTaskData = ref([]);

// 任务类型英转中
function typeNameTrans(type) {
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
function query(page) {
  axios
    .get('/v1/tasks/recycle-bin', { page_num: page })
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
            deleteTime: formatTime(task.update_time, 'yyyy-MM-dd hh:mm:ss')
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
    key: 'name'
  },
  {
    title: '类型',
    key: 'type',
    align: 'center'
  },
  {
    title: '创建人',
    align: 'center',
    key: 'originator'
  },
  {
    title: '删除时间',
    align: 'center',
    key: 'deleteTime'
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
              warning('恢复任务', '您确定要恢复此任务吗？', () => {
                editTask(row.id, { is_delete: false });
                query(recycleBinTaskPagination.value.page);
              });
            }
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
            }
          },
          '彻底删除'
        )
      ];
    }
  }
];

// tab名称
const menu = ref([
  {
    id: 0,
    text: '个人概览',
    name: 'dashboard'
  },
  {
    id: 1,
    text: '需求中心',
    name: 'require'
  },
  {
    id: 2,
    text: '任务看板',
    name: 'task'
  },
  {
    id: 3,
    text: '测试设计',
    name: 'design'
  },
  {
    id: 4,
    text: '测试执行',
    name: 'testing'
  }
]);

//获取里程碑列表
function getMilestones() {
  axios.get('/v2/milestone', { page_num: 1, page_size: 999999 }).then((response) => {
    if (response?.data) {
      milestones.value =
        response.data?.items?.map((item) => ({
          label: item.name,
          value: String(item.id)
        })) || [];
    }
  });
}

// 初始化
function initCondition() {
  const allRequest = [
    axios.get('/v1/task/status'),
    axios.get(`/v1/org/${storage.getValue('orgId')}/users`, {
      page_num: 1,
      page_size: 9999
    }),
    getGroup({ page_size: 99999, page_num: 1 })
  ];
  getMilestones();
  Promise.allSettled(allRequest).then((responses) => {
    executors.value = [];
    participants.value = [];
    originators.value = [];
    statusOptions.value = [];
    if (responses[0].value?.data) {
      responses[0].value.data?.forEach((item) => {
        statusOptions.value.push({
          label: item.name,
          value: item.id
        });
      });
    }
    if (responses[1].value?.data) {
      responses[1].value.data?.items?.forEach((item) => {
        const option = {
          label: item.gitee_name,
          value: item.gitee_id
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
          value: item.id
        };
        executors.value.push(option);
        participants.value.push(option);
      });
    }
  });
}

// 页面切换
function menuClick(item, index) {
  menuSelect.value = index;
  router.push(`/home/workflow/${item.name}`);
  index === 2 ? (isTask.value = true) : (isTask.value = false);
  item.name === 'task' ? (backable.value = false) : (backable.value = true);
}

// 视图切换
function toggleView() {
  store.commit('taskManage/toggleView');
}

// 显示回收站按钮
function showRecycleBin() {
  showRecycleBinModal.value = true;
  recycleBinTaskLoading.value = true;
  query(1);
}

// 回收站表格页数变动
function recycleBinTablePageChange(currentPage) {
  if (!recycleBinTaskLoading.value) {
    recycleBinTaskLoading.value = true;
    query(currentPage);
  }
}

// 筛选条件
const filterRule = ref([
  {
    path: 'title',
    name: '名称',
    type: 'input'
  },
  {
    path: 'type',
    name: '类型',
    type: 'select',
    options: [
      { label: '个人任务', value: 'PERSON' },
      { label: '团队任务', value: 'GROUP' },
      { label: '组织任务', value: 'ORGANIZATION' },
      { label: '版本任务', value: 'VERSION' }
    ]
  },
  {
    path: 'originator',
    name: '创建者',
    type: 'select',
    options: originators
  },
  {
    path: 'executor_id',
    name: '执行者',
    type: 'select',
    options: executors
  },
  {
    path: 'participant_id',
    name: '协助人',
    type: 'multipleselect',
    options: participants
  },
  {
    path: 'milestone_id',
    name: '里程碑',
    type: 'multipleselect',
    options: milestones
  },
  {
    path: 'status_id',
    name: '状态',
    type: 'select',
    options: statusOptions
  },
  {
    path: 'deadline',
    name: '截止日期',
    type: 'enddate'
  },
  {
    path: 'start_time',
    name: '开始日期',
    type: 'startdate'
  }
]);

function filterchange(filterArray) {
  let model = {
    title: null,
    executor_id: null,
    originator: null,
    participant_id: null,
    milestone_id: null,
    status_id: null,
    start_time: null,
    deadline: null,
    type: null
  };

  filterArray.forEach((v) => {
    model[v.path] = v.value;
  });

  if (model.deadline > 0) {
    model.deadline = formatTime(model.deadline, 'yyyy-MM-dd hh:mm:ss');
  }
  if (model.start_time > 0) {
    model.start_time = formatTime(model.start_time, 'yyyy-MM-dd hh:mm:ss');
  }
  model.page_num = 1;
  model.page_size = 99999999;
  document.dispatchEvent(
    new CustomEvent('searchTask', {
      detail: model
    })
  );
}

const watchRoute = () => {
  isDesign.value = false;
  if (router.currentRoute.value.path === '/home/workflow/dashboard') {
    menuSelect.value = 0;
    isTask.value = false;
    backable.value = false;
  } else if (router.currentRoute.value.path === '/home/workflow/require') {
    menuSelect.value = 1;
    isTask.value = false;
    backable.value = false;
  } else if (router.currentRoute.value.path === '/home/workflow/task') {
    menuSelect.value = 2;
    isTask.value = true;
    backable.value = false;
  } else if (router.currentRoute.value.path.startsWith('/home/workflow/testing')) {
    menuSelect.value = 4;
    isTask.value = false;
    backable.value = false;
  } else if (router.currentRoute.value.path === '/home/workflow/report') {
    menuSelect.value = 2;
    isTask.value = true;
    backable.value = true;
  } else if (router.currentRoute.value.path === '/home/workflow/distribution') {
    menuSelect.value = 2;
    isTask.value = true;
    backable.value = true;
  } else if (router.currentRoute.value.path === '/home/workflow/design') {
    menuSelect.value = 3;
    isTask.value = false;
    backable.value = false;
    isDesign.value = true;
  }
};

export {
  watchRoute,
  filterchange,
  menuSelect,
  isTask,
  kanban,
  backable,
  originators,
  executors,
  participants,
  statusOptions,
  menu,
  milestones,
  initCondition,
  menuClick,
  toggleView,
  recycleBinTaskTable,
  recycleBinTaskLoading,
  recycleBinTaskColumns,
  recycleBinTaskData,
  showRecycleBinModal,
  showRecycleBin,
  recycleBinTaskPagination,
  recycleBinTablePageChange,
  filterRule,
  isDesign,
  isDesignTemplate
};
