import { ref, h } from 'vue';
import myRouter from '@/router';
import { getDetail } from '@/views/taskManage/task/modules/taskDetail.js';
import { initData as initDataKanban } from '@/views/taskManage/task/modules/kanbanAndTable.js';
import { NIcon } from 'naive-ui';
import { Circle, CircleCheck, CircleMinus, CircleX } from '@vicons/tabler';
import axios from '@/axios';
import { formatTime } from '@/assets/utils/dateFormatUtils.js';
import { getCaseCommit } from '@/api/get';
import userInfo from '@/components/user/userInfo.vue';

const vmachineClick = (router) => {
  router.push('/home/resource-pool/vmachine');
};
const handleGiteeClick = () => {
  window.open('https://gitee.com/openeuler/radiaTest');
};

const showWorkbench = ref(false); // 显示工作台
const workbench = ref(null); // 工作台DOM

const layout = ref([
  { x: 0, y: 0, w: 8, h: 10, i: 'personal' },
  { x: 8, y: 0, w: 4, h: 48, minH: 15, i: 'machine' },
  { x: 0, y: 7, w: 4, h: 38, minH: 15, i: 'tasks' },
  { x: 4, y: 7, w: 4, h: 38, minH: 15, i: 'cases' }
]);

const personalDataOverview = ref({
  todayTasksCount: 0,
  weekTasksCount: 0,
  monthTasksCount: 0,
  todayCasesCount: 0,
  weekCasesCount: 0,
  monthCasesCount: 0
});

// 任务卡片分页
const tasksPagination = ref({
  page: 1,
  pageCount: 1, //总页数
  pageSize: 10
});

let taskType = 'not_accomplish';
let taskTitle = '';

let machineType = 'virtual';
let machineName = '';

const myTasksCol = ref([
  {
    title: '状态',
    key: 'statusIcon',
    align: 'center',
    width: '60px',
    render(rowData) {
      let icon = null;
      let color = null;
      switch (rowData.status) {
        case 1:
          icon = Circle;
          color = '#8c92a4';
          break;
        case 2:
          icon = CircleMinus;
          break;
        case 5:
          icon = CircleCheck;
          color = '#4baf50';
          break;
        case '已取消':
          icon = CircleX;
          color = '#ec0019';
          break;
        default:
          icon = CircleMinus;
          break;
      }

      return h(
        NIcon,
        { size: 20, color },
        {
          default: () => h(icon, { style: 'vertical-aligh:middle' })
        }
      );
    }
  },
  {
    title: '任务名称',
    key: 'taskName',
    align: 'left',
    ellipsis: true
  },
  {
    title: '任务类型',
    key: 'taskType',
    align: 'center',
    width: '100px',
    render(rowData) {
      let type = '';
      switch (rowData.taskType) {
        case 'PERSON':
          type = '个人';
          break;
        case 'GROUP':
          type = '团队';
          break;
        case 'ORGANIZATION':
          type = '组织';
          break;
        case 'VERSION':
          type = '版本';
          break;
        default:
          type = '';
          break;
      }

      return type;
    }
  },
  {
    title: '里程碑',
    key: 'milestone',
    width: '100px',
    align: 'center',
    ellipsis: true
  },
  {
    title: '截止时间',
    key: 'endTime',
    align: 'center',
    ellipsis: true
  }
]);

const myTasksData = ref([]);
const tasksloading = ref(false);

function getTaskData() {
  tasksloading.value = true;
  axios
    .get('/v1/user/task/info', {
      task_type: taskType,
      task_title: taskTitle,
      page_num: tasksPagination.value.page,
      page_size: tasksPagination.value.pageSize
    })
    .then((res) => {
      myTasksData.value = [];
      tasksloading.value = false;
      tasksPagination.value.pageCount = res.data.pages;
      personalDataOverview.value = {
        todayTasksCount: res.data.today_tasks_count,
        weekTasksCount: res.data.week_tasks_count,
        monthTasksCount: res.data.month_tasks_count,
        todayCasesCount: 0,
        weekCasesCount: 0,
        monthCasesCount: 0
      };
      if (res.data.items) {
        res.data.items.forEach((v, i) => {
          let milestone = '无';
          if (v.milestone) {
            milestone = v.milestone.name;
          } else if (v.milestones) {
            milestone = v.milestones.map((v2) => v2.name).join(',');
          }

          myTasksData.value.push({
            key: i,
            id: v.id,
            taskName: v.title,
            taskType: v.type,
            milestone,
            endTime: formatTime(v.deadline, 'yyyy-MM-dd hh:mm:ss'),
            status: v.status_id
          });
        });
      }
    })
    .catch((err) => {
      tasksloading.value = false;
      window.$message?.error(err.data?.error_msg || err.message || '未知错误');
    });
}

function handleTasksPageChange(currentPage) {
  tasksPagination.value.page = currentPage;
  getTaskData();
}

const taskActive = ref('0'); // 我的任务活动tab

function taskWorkbenchClick(e) {
  tasksPagination.value.page = 1;
  taskActive.value = e.target.dataset.index;
  taskTitle = '';
  switch (taskActive.value) {
    case '0':
      taskType = 'not_accomplish';
      break;
    case '1':
      taskType = 'today';
      break;
    case '2':
      taskType = 'week';
      break;
    case '3':
      taskType = 'overtime';
      break;
    case '4':
      taskType = 'all';
      break;
    default:
      break;
  }
  getTaskData();
}

function myTasksRowProps(rowData) {
  return {
    style: 'cursor: pointer;',
    onClick: () => {
      myRouter.push('/home/tm/task');
      initDataKanban(() => {
        getDetail(rowData);
      });
    }
  };
}

const taskSearchValue = ref(null);

function taskSearch() {
  taskTitle = taskSearchValue.value;
  tasksPagination.value.page = 1;
  getTaskData();
}

const personalRefresh = ref(null); // 个人数据刷新DOM
let anglePersonal = 0;
function personalRefreshClick() {
  anglePersonal -= 360;
  personalRefresh.value.style.transform = `rotate(${anglePersonal}deg)`;
}

const taskRefresh = ref(null); // 我的任务刷新DOM
let angleTask = 0;
function taskRefreshClick() {
  angleTask -= 360;
  taskRefresh.value.style.transform = `rotate(${angleTask}deg)`;
  getTaskData();
}

const caseRefresh = ref(null); // 我的用例刷新DOM
let angleCase = 0;
function caseRefreshClick() {
  angleCase -= 360;
  caseRefresh.value.style.transform = `rotate(${angleCase}deg)`;
}

const myCasesCol = ref([
  {
    title: '评审标题',
    key: 'title',
    align: 'center'
  },
  {
    title: '评审人',
    key: 'reviewer_name',
    align: 'center',
    render: (row) => {
      return h(userInfo, {
        userInfo: row.reviewer
      });
    }
  },
  {
    title: '描述',
    key: 'description',
    align: 'center'
  }
]);
const myCasePagination = ref({
  page: 1,
  pageCount: 1, //总页数
  pageSize: 10
});

const myCasesData = ref([]);

const machineActive = ref('0'); // 我的机器活动tab

const myMachineData = ref([]);

function getMachineData() {
  axios
    .get('/v1/user/machine/info', {
      machine_type: machineType,
      machine_name: machineName,
      page_num: 1,
      page_size: 999999999
    })
    .then((res) => {
      myMachineData.value = [];
      if (res.data.items) {
        res.data.items.forEach((v, i) => {
          myMachineData.value.push({
            key: i,
            status: v.status,
            ip: v.ip,
            bmc_ip: v.bmc_ip,
            milestone: v.milestone,
            description: v.description
          });
        });
      }
    })
    .catch((err) => {
      window.$message?.error(err.data?.error_msg || err.message || '未知错误');
    });
}

function machineWorkbenchClick(e) {
  machineActive.value = e.target.dataset.index;
  machineName = '';

  switch (machineActive.value) {
    case '0':
      machineType = 'virtual';
      break;
    case '1':
      machineType = 'physics';
      break;
    default:
      break;
  }
  getMachineData();
}

const machineSearchValue = ref(null);

function machineSearch() {
  machineName = machineSearchValue.value;
  getMachineData();
}

const myMachineColVirtual = ref([
  {
    title: '状态',
    key: 'statusIcon',
    align: 'center',
    // width: '20px',
    render(rowData) {
      let icon = null;
      let color = null;
      switch (rowData.status) {
        case 'on':
          icon = CircleMinus;
          break;
        case 'off':
          icon = Circle;
          color = '#8c92a4';
          break;
        default:
          icon = CircleMinus;
          color = '#8c92a4';
          break;
      }

      return h(
        NIcon,
        { size: 20, color },
        {
          default: () => h(icon, { style: 'vertical-aligh:middle' })
        }
      );
    }
  },
  {
    title: 'IP',
    key: 'ip',
    align: 'center'
  },
  {
    title: '里程碑',
    key: 'milestone',
    align: 'center'
  },
  {
    title: '描述',
    key: 'description',
    align: 'center'
  }
]);

const myMachineColPhysics = ref([
  {
    title: '状态',
    key: 'statusIcon',
    align: 'center',
    // width: '20px',
    render(rowData) {
      let icon = null;
      let color = null;
      switch (rowData.status) {
        case 'on':
          icon = CircleMinus;
          break;
        case 'off':
          icon = Circle;
          color = '#8c92a4';
          break;
        default:
          icon = CircleMinus;
          color = '#8c92a4';
          break;
      }

      return h(
        NIcon,
        { size: 20, color },
        {
          default: () => h(icon, { style: 'vertical-aligh:middle' })
        }
      );
    }
  },
  {
    title: 'IP',
    key: 'ip',
    align: 'center'
  },
  {
    title: 'BMC IP',
    key: 'bmc_ip',
    align: 'center'
  },
  {
    title: '描述',
    key: 'description',
    align: 'center'
  }
]);

const machineRefresh = ref(null); // 我的机器刷新DOM
let angleMachine = 0;
function machineRefreshClick() {
  angleMachine -= 360;
  machineRefresh.value.style.transform = `rotate(${angleMachine}deg)`;
  getMachineData();
}
const caseLoading = ref(false);
function getMyCase(status = 'open') {
  caseLoading.value = true;
  getCaseCommit({
    page_num: myCasePagination.value.page,
    page_size: myCasePagination.value.pageSize,
    status
  })
    .then((res) => {
      caseLoading.value = false;
      myCasesData.value = res.data?.items || [];
      myCasePagination.value.pageCount = res.data.pages;
      personalDataOverview.value.todayCasesCount = res.data.today_case_count;
      personalDataOverview.value.weekCasesCount = res.data.week_case_count;
      personalDataOverview.value.monthCasesCount = res.data.month_case_count;
    })
    .catch(() => {
      caseLoading.value = false;
    });
}
const caseActive = ref('0');
function caseWorkbenchClick(e) {
  myCasePagination.value.page = 1;
  caseActive.value = e.target.dataset.index;
  const typeArr = ['open', 'accepted', 'rejected', 'all'];
  getMyCase(typeArr[caseActive.value]);
}
function handleCasePageChange(page) {
  myCasePagination.value.page = page;
  getMyCase();
}
function initData() {
  getTaskData();
  getMachineData();
  getMyCase();
}

function resizedEvent(i, newH, newW, newHPx) {
  if (i === 'tasks') {
    tasksPagination.value.page = 1;
    tasksPagination.value.pageSize = Math.round((newHPx - 240) / 47, 0);
    getTaskData();
  }
}

function debounce(func, delay) {
  let timeout;
  return (...args) => {
    if (args[0].deltaY > 0) {
      showWorkbench.value = true;
    }
    clearTimeout(timeout);
    timeout = setTimeout(() => {
      if (args[0].deltaY > 0) {
        func.apply(this, args);
      }
    }, delay);
  };
}
// 滚轮下滚
const handleWheelDown = debounce(initData, 1000);

export {
  tasksloading,
  handleTasksPageChange,
  tasksPagination,
  resizedEvent,
  machineSearch,
  machineSearchValue,
  getMachineData,
  vmachineClick,
  handleGiteeClick,
  showWorkbench,
  workbench,
  layout,
  personalDataOverview,
  handleWheelDown,
  personalRefresh,
  personalRefreshClick,
  machineRefresh,
  machineRefreshClick,
  taskRefresh,
  taskRefreshClick,
  caseRefresh,
  caseRefreshClick,
  taskActive,
  taskWorkbenchClick,
  myTasksCol,
  myTasksData,
  myTasksRowProps,
  myCasesCol,
  myCasesData,
  machineActive,
  machineWorkbenchClick,
  myMachineColVirtual,
  myMachineColPhysics,
  myMachineData,
  initData,
  taskSearchValue,
  taskSearch,
  myCasePagination,
  handleCasePageChange,
  caseLoading,
  getMyCase,
  caseActive,
  caseWorkbenchClick
};
