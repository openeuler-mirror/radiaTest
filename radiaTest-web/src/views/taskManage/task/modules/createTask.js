import { ref, nextTick, toRef, h } from 'vue';
import store from '@/store/index';
import axios from '@/axios';
import { formatTime } from '@/assets/utils/dateFormatUtils.js';
import { storage } from '@/assets/utils/storageUtils';
import { showLoading, detailTask, getDetailTask } from './taskDetail.js';
import { personArray, initData } from './kanbanAndTable.js';
import { NAvatar } from 'naive-ui';
import { getGroup as getGroups, getAllMilestone, getRelationTaskList, getOrgGroup, getOrgUser } from '@/api/get.js';

const showVersionTaskModal = ref(false); // 显示创建版本任务窗口
const groups = ref([]); // 执行团队选项数组
const showNewTaskDrawer = toRef(store.state.taskManage, 'showNewTaskDrawer'); // 显示新建任务
const formRef = ref(null); // 创建任务表单
const formRefVersion = ref(null); // 创建版本任务表单
const showRelation = ref(true); //是否显示关联任务

// 新建任务参数
const model = ref({
  title: null,
  type: null,
  group: null,
  executor: null,
  start_time: null,
  deadline: null,
  orgTask: '',
  taskType: '',
  fatherTask: null,
  childTask: null,
  keywords: null,
  abstract: null,
  abbreviation: null
});

// 新建版本任务参数
const modelVersion = ref({
  title: null,
  group: null,
  executor_id: '',
  executor: null,
  start_time: null,
  deadline: null,
  milestone: null,
  keywords: null,
  abstract: null,
  taskType: '',
  abbreviation: null,
  fatherTask: null,
  childTask: null
});

// 创建版本任务表单检验规则
const rulesVersion = ref({
  title: {
    required: true,
    message: '任务名称必填',
    trigger: ['blur', 'input']
  },
  executor_id: {
    required: true,
    message: '执行者必填',
    trigger: ['blur', 'change']
  },
  milestone: {
    type: 'number',
    required: true,
    message: '里程碑必选',
    trigger: ['blur', 'change']
  },
  start_time: {
    type: 'number',
    required: true,
    message: '开始日期必填',
    trigger: ['blur', 'change']
  },
  deadline: {
    type: 'number',
    required: true,
    message: '截止日期必填',
    trigger: ['blur', 'change']
  }
});

// 任务类型
const taskTypes = ref([
  { label: '个人任务', value: 'PERSON' },
  { label: '团队任务', value: 'GROUP' },
  { label: '组织任务', value: 'ORGANIZATION' }
]);

// 任务类型
const task = {
  PERSON: '个人任务',
  GROUP: '团队任务',
  ORGANIZATION: '组织任务',
  VERSION: '版本任务'
};

// 组织任务执行者选项
const orgOptions = ref([
  {
    label: '团队',
    value: 'GROUP',
    depth: 1,
    isLeaf: false
  },
  {
    label: '个人',
    value: 'PERSON',
    depth: 1,
    isLeaf: false
  }
]);

// 创建任务表单检验规则
const rules = ref({
  title: {
    required: true,
    message: '任务名称必填',
    trigger: ['blur', 'input']
  },
  type: {
    required: true,
    message: '任务类型必填',
    trigger: ['blur', 'change']
  },
  group: {
    required: true,
    message: '执行团队必填',
    trigger: ['blur', 'change']
  },
  executor: {
    required: true,
    message: '执行者必填',
    trigger: ['blur', 'change']
  },
  orgTask: {
    required: true,
    message: '执行者必填',
    trigger: ['blur', 'change']
  },
  start_time: {
    type: 'number',
    required: true,
    message: '开始日期必填',
    trigger: ['blur', 'change']
  },
  deadline: {
    type: 'number',
    required: true,
    message: '截止日期必填',
    trigger: ['blur', 'change']
  }
});

// 设置创建任务等级、状态id
function createBaseTask(element) {
  model.value = {
    title: null,
    type: null,
    group: null,
    executor: null,
    start_time: null,
    deadline: null,
    orgTask: '',
    taskType: '',
    fatherTask: null,
    childTask: null,
    keywords: null,
    abstract: null,
    abbreviation: null
  };
  detailTask.level = 0;
  detailTask.statusId = element.id;
  if (!showRelation.value) {
    model.value.fatherTask = null;
    showRelation.value = true;
  }
}

// 获取执行团队
function getGroup() {
  showLoading.value = true;
  groups.value = [];
  getGroups({
    page_num: 1,
    page_size: 99999
  })
    .then((res) => {
      showLoading.value = false;
      if (res?.data?.items) {
        for (const item of res.data?.items) {
          groups.value.push({
            label: item.name,
            value: String(item.id),
            avatar_url: item.avatar_url
          });
        }
      }
    })
    .catch((err) => {
      window.$message?.error(err.data?.error_msg || '未知错误');
      showLoading.value = false;
    });
}

// 任务类型变更回调
function taskTypeChange(value) {
  model.value.type = value;
  model.value.taskType = 'PERSON';
  if (model.value.type === 'PERSON') {
    personArray.value = [
      {
        label: storage.getValue('user_name'),
        value: String(storage.getValue('user_id'))
      }
    ];
    groups.value = [{ label: '个人', value: '0' }];
    nextTick(() => {
      model.value.group_id = '0';
      model.value.executor = String(storage.getValue('user_id'));
    });
  } else {
    model.value.group_id = '';
    model.value.executor = '';
  }
  if (model.value.type === 'GROUP') {
    getGroup();
  }
}

// 获取执行团队下属人员
function getUserByGroup(value) {
  model.value.group_id = value;
  model.value.executor = '';
  showLoading.value = true;
  personArray.value = [];
  axios
    .get(`/v1/groups/${model.value.group_id}/users`, {
      page_num: 1,
      page_size: 99999
    })
    .then((res) => {
      showLoading.value = false;
      for (const item of res.data.items) {
        personArray.value.push({
          label: item.user_name,
          value: String(item.user_id),
          avatar_url: item.avatar_url
        });
      }
    })
    .catch((err) => {
      showLoading.value = false;
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

// 取消新建任务
function cancelCreateTask() {
  store.commit('taskManage/toggleNewTaskDrawer');
  model.value = {
    title: null,
    type: null,
    group: null,
    executor: null,
    start_time: null,
    deadline: null,
    orgTask: '',
    taskType: ''
  };
}

// 组织任务设置选定值
function orgSelect(value, { type }) {
  model.value.orgTask = value;
  model.value.taskType = type;
}

// 组织任务获取团队或个人
function handleLoad(option) {
  return new Promise((resolve, reject) => {
    if (option.value === 'GROUP') {
      getOrgGroup(storage.getLocalValue('unLoginOrgId').id, {
        page_num: 1,
        page_size: 99999
      })
        .then((res) => {
          option.children = [];
          for (const item of res.data.items) {
            option.children.push({
              label: item.name,
              value: String(item.id),
              avatar_url: item.avatar_url,
              type: 'GROUP'
            });
          }
          resolve();
        })
        .catch((err) => {
          window.$message?.error(err.data.error_msg || '未知错误');
          reject(new Error('error'));
        });
    } else {
      getOrgUser(storage.getLocalValue('unLoginOrgId').id, {
        page_num: 1,
        page_size: 99999
      })
        .then((res) => {
          option.children = [];
          for (const item of res.data.items) {
            option.children.push({
              label: item.user_name,
              value: String(item.user_id),
              avatar_url: item.avatar_url,
              type: 'PERSON'
            });
          }
          resolve();
        })
        .catch((err) => {
          window.$message?.error(err.data.error_msg || '未知错误');
          reject(new Error('error'));
        });
    }
  });
}

// 退出创建版本任务
function cancelCreateVersionTask() {
  showVersionTaskModal.value = false;
}

const milestoneOptions = ref([]);

// 显示创建版本任务
function createVersionTask() {
  modelVersion.value = {
    title: null,
    group: null,
    executor_id: '',
    executor: null,
    start_time: null,
    deadline: null,
    milestone: null,
    keywords: null,
    abstract: null,
    taskType: '',
    abbreviation: null,
    fatherTask: null,
    childTask: null
  };
  store.commit('taskManage/toggleNewTaskDrawer');
  showVersionTaskModal.value = true;
  getAllMilestone({ paged: false }).then((res) => {
    milestoneOptions.value = [];
    res.data?.items?.forEach((v) => {
      milestoneOptions.value.push({
        label: v.name,
        value: v.id
      });
    });
  });
}

// 确认创建版本任务
function createVersionTaskBtn() {
  formRefVersion.value.validate((error) => {
    if (error) {
      window.$message?.error('请填写相关信息');
    } else {
      axios
        .post('/v1/tasks', {
          is_version_task: true,
          type: 'VERSION',
          title: modelVersion.value.title,
          status_id: detailTask.statusId,
          executor_type: modelVersion.value.taskType,
          parent_id: modelVersion.value.fatherTask,
          child_id: modelVersion.value.childTask,
          executor_id: modelVersion.value.executor_id,
          start_time: formatTime(new Date(modelVersion.value.start_time), 'yyyy-MM-dd'),
          deadline: formatTime(new Date(modelVersion.value.deadline), 'yyyy-MM-dd'),
          keywords: modelVersion.value.keywords,
          abstract: modelVersion.value.abstract,
          abbreviation: modelVersion.value.abbreviation,
          milestone_id: modelVersion.value.milestone_id
        })
        .then(() => {
          if (showRelation.value) {
            initData();
          } else {
            getDetailTask();
          }
          window.$message?.success('任务创建成功!');
          cancelCreateVersionTask();
          showLoading.value = false;
        })
        .catch((err) => {
          showLoading.value = false;
          window.$message?.error(err.data.error_msg || '未知错误');
        });
    }
  });
}
function versionSelect(value, { type }) {
  modelVersion.value.executor_id = value;
  modelVersion.value.taskType = type;
}

// 新建任务
function createTask(e, versionTask = false) {
  formRef.value.validate((error) => {
    if (!error) {
      showLoading.value = true;
      axios
        .post('/v1/tasks', {
          is_version_task: versionTask,
          title: model.value.title,
          level: Number(detailTask.level) + 1,
          type: model.value.type,
          status_id: detailTask.statusId,
          executor_type: model.value.taskType,
          parent_id: model.value.fatherTask,
          child_id: model.value.childTask,
          group_id: model.value.type === 'GROUP' ? Number(model.value.group_id) : null,
          executor_id: model.value.type === 'ORGANIZATION' ? model.value.orgTask : model.value.executor,
          start_time: formatTime(new Date(model.value.start_time), 'yyyy-MM-dd'),
          deadline: formatTime(new Date(model.value.deadline), 'yyyy-MM-dd'),
          keywords: model.value.keywords,
          abstract: model.value.abstract,
          abbreviation: model.value.abbreviation
        })
        .then(() => {
          if (showRelation.value) {
            initData();
          } else {
            getDetailTask();
          }
          window.$message?.success('任务创建成功!');
          cancelCreateTask();
          showLoading.value = false;
        })
        .catch((err) => {
          showLoading.value = false;
          window.$message?.error(err?.data?.error_msg || '未知错误');
        });
    } else {
      window.$message?.error('请填写相关信息');
    }
  });
}

// 执行团队、执行者自定义选项渲染函数
function renderLabel(option) {
  return h(
    'div',
    {
      style: {
        display: 'flex',
        alignItems: 'center',
        'justify-content': 'left'
      }
    },
    [
      h(NAvatar, {
        src: option.avatar_url,
        round: true,
        size: 'small'
      }),
      h(
        'div',
        {
          style: {
            marginLeft: '12px',
            padding: '4px 0',
            width: '110px'
          }
        },
        [h('div', null, [option.label])]
      )
    ]
  );
}

const relationTasks = ref([]);
function getRelationTask() {
  relationTasks.value = [];
  getRelationTaskList().then(res => {
    res.data.forEach((item) => {
      relationTasks.value.push({
        label: item.title,
        value: item.id
      });
    });
  });
}

export {
  milestoneOptions,
  showRelation,
  relationTasks,
  showVersionTaskModal,
  groups,
  showNewTaskDrawer,
  formRef,
  formRefVersion,
  model,
  modelVersion,
  rulesVersion,
  taskTypes,
  task,
  orgOptions,
  rules,
  createBaseTask,
  getGroup,
  getRelationTask,
  taskTypeChange,
  getUserByGroup,
  cancelCreateTask,
  orgSelect,
  handleLoad,
  createVersionTask,
  createVersionTaskBtn,
  cancelCreateVersionTask,
  createTask,
  versionSelect,
  renderLabel
};
