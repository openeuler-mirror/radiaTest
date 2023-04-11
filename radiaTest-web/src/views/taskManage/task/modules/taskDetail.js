import { reactive, ref, nextTick, h, computed } from 'vue';
import store from '@/store/index';
import { DeleteOutlined } from '@vicons/antd';
import { ReportAnalytics, ArrowsSplit } from '@vicons/tabler';
import { NIcon, NButton, NDropdown } from 'naive-ui';
import axios from '@/axios';
import { formatTime } from '@/assets/utils/dateFormatUtils.js';
// import { storage } from '@/assets/utils/storageUtils';
import { initData, getTask } from './kanbanAndTable.js';
import { createTask, model, showRelation } from './createTask';
import { generateMdFile, md } from './mdFile';
import { unkonwnErrorMsg } from '@/assets/utils/description';
import tinymce from 'tinymce/tinymce';
import 'tinymce/themes/silver/theme'; // 引用主题文件
import 'tinymce/icons/default'; // 引用图标文件
import 'tinymce/plugins/image'; //图片
import 'tinymce/plugins/imagetools'; //图片工具
import 'tinymce/plugins/nonbreaking';
import { workspace } from '@/assets/config/menu.js';

const showModal = ref(false); // 显示任务详情页
const showCaseModal = ref(false); // 显示关联测试用例表格
const modalData = ref({}); // 任务详情页数据
const showTaskTitleInput = ref(false); // 显示详情页任务名称文本框
const showBackMenu = ref(false); // 显示返回父任务按钮
const titleInputRef = ref(null); // 任务名称文本框
const showPopoverExecutor = ref(false); // 显示责任人选择框
const showPopoverExecutors = ref(false); // 执行团队显示责任人
const showPopoverHelper = ref(false); // 显示协助人选择框
const showMilepost = ref(false); // 显示里程碑选择菜单
const showClosingTime = ref(false); // 截止时间选项显示/编辑切换
const showContentInput = ref(false); // 内容选项显示/编辑切换
const showFooterContent = ref('comment'); // 任务详情底部显示内容，默认：评论
const contentInputRef = ref(null); // 内容选项文本框
const commentInput = ref(null); // 评论数据
const taskName = ref(''); // 任务名称
const checkedRowKeys = ref([]); // 关联测试用例选择数组
const loadingRef = ref(false); // 关联测试用例表格加载状态
const caseData = ref([]); // 关联测试用例表格数据
const hasFatherTask = ref(true); // 是否有父任务
const hasChildTask = ref(false); // 是否有子任务
const showAssociatedTask = ref(true); // 展示关联父任务按钮
const showAssociatedChildTask = ref(true); // 展示关联子任务按钮
const associatedTaskValue = ref(null); // 关联父任务选值
const associatedChildTaskValue = ref(null); // 关联子任务选值
const childTaskArray = ref(['子任务1', '子任务2', '子任务3']); // 子任务数组
const showLoading = ref(false); // 显示加载
const fatherTaskArrayTemp = ref([]); // 父任务搜索后数组
const childTaskArrayTemp = ref([]); // 子任务搜索后数组
const fatherTaskLoading = ref(false); // 父任务搜索加载状态
const childTaskLoading = ref(false); // 子任务搜索加载状态
const showReportModal = ref(false); // 生成报告弹窗
const reportArray = ref([]); // 报告数组
const editStatus = ref(false); // 编辑状态
const showEditTaskDetailBtn = ref(true); // 显示编辑任务按钮

const frameArray = ref();

// 富文本配置
const init = {
  language_url: require('@/assets/tinymce/zh_CN.js'), // 中文语言包路径
  language: 'zh_CN',
  skin_url: '/tinymce/skins/ui/oxide', // 编辑器皮肤样式
  content_css: '/tinymce/skins/content/default/content.min.css',
  menubar: false, // 隐藏菜单栏
  height: 200,
  width: '100%',
  toolbar_mode: 'scrolling', // 工具栏模式
  plugins: 'image imagetools nonbreaking',
  toolbar:
    'undo redo fontsizeselect fontselect|underline forecolor backcolor bold italic strikethrough image subscript superscript removeformat|',
  content_style: 'p {margin: 5px 0; font-size: 14px}',
  fontsize_formats: '12px 14px 16px 18px 24px 36px 48px 56px 72px',
  font_formats:
    '微软雅黑=Microsoft YaHei,Helvetica Neue,PingFang SC,sans-serif;苹果苹方=PingFang SC,Microsoft YaHei,sans-serif;宋体=simsun,serif;仿宋体=FangSong,serif;黑体=SimHei,sans-serif;Arial=arial,helvetica,sans-serif;Arial Black=arial black,avant garde;Book Antiqua=book antiqua,palatino;',
  branding: false, // 隐藏右下角技术支持
  elementpath: false, // 隐藏底栏的元素路径
  nonbreaking_force_tab: true,
  resize: false, // 禁止改变大小
  statusbar: false, // 隐藏底部状态栏
  // 图片上传
  images_upload_handler(blobInfo, success) {
    let reader = new FileReader();
    reader.readAsDataURL(blobInfo.blob());
    reader.onload = function () {
      success(this.result);
    };
  }
};

// 渲染图标
function renderIcon(icon) {
  return () => {
    return h(NIcon, null, {
      default: () => h(icon)
    });
  };
}

// 任务等级详情
const detailTask = reactive({
  id: '',
  level: 0,
  parentId: ''
});

// 父子任务关联、查询
function familyTaskOperator(option) {
  return new Promise((resolve, reject) => {
    axios
      .get(`/v1/tasks/${detailTask.taskId}/family`, option)
      .then((res) => {
        fatherTaskLoading.value = false;
        childTaskLoading.value = false;
        resolve(res);
      })
      .catch((err) => {
        fatherTaskLoading.value = false;
        childTaskLoading.value = false;
        window.$message?.error(err.data.error_msg || err.message || unkonwnErrorMsg);
        reject(err);
      });
  });
}

//用例查询操作
function caseOperator(option) {
  return new Promise((resolve, reject) => {
    axios
      .get(`/v1/tasks/${detailTask.taskId}/cases`, option)
      .then((res) => {
        resolve(res);
      })
      .catch((err) => {
        reject(err);
      });
  });
}

//获取评论
function getTaskComment() {
  axios
    .get(`/v1/tasks/${detailTask.taskId}/comment`)
    .then((res) => {
      modalData.value.comments = res.data;
    })
    .catch((errors) => {
      window.$message?.error(errors.data.error_msg || errors.message || '未知错误');
    });
}

//获取协助人
function getTaskHelper() {
  axios
    .get(`/v1/tasks/${detailTask.taskId}/participants`)
    .then((res) => {
      modalData.value.helper = res.data;
    })
    .catch((errors) => {
      window.$message?.error(errors.data.error_msg || errors.message || '未知错误');
    });
}

// 任务详情右上角菜单选项
const menuOptions = ref([
  {
    label: '删除任务',
    key: 'deleteTask',
    icon: renderIcon(DeleteOutlined),
    disabled: false
  },
  {
    label: '生成模板报告',
    key: 'reporting',
    icon: renderIcon(ReportAnalytics)
  },
  {
    label: '分配任务',
    key: 'distributeTask',
    icon: renderIcon(ArrowsSplit)
  }
]);

const editRole = computed(() => {
  return true;
  // return (
  //   modalData.value.detail?.originator?.user_id ===
  //   String(storage.getValue('user_id'))
  // );
});

// 获取任务详情数据
function getDetailTask() {
  return new Promise((resolve, reject) => {
    showLoading.value = true;
    axios
      .get(`/v1/tasks/${detailTask.taskId}`)
      .then((res) => {
        showLoading.value = false;
        modalData.value.detail = res.data;
        detailTask.parentId = res.data.parent_id;
        showModal.value = true;
        menuOptions.value[0].disabled = !editRole.value;
        resolve('success');
      })
      .catch((errors) => {
        showLoading.value = false;
        window.$message?.error(errors.data.error_msg || errors.message || '未知错误');
        reject(new Error('false'));
      });
  });
}
const caseLoading = ref(false);
// let expandMilestoneId = '';
// function expandChange ({ name }) {
//   expandMilestoneId = name;
// }

// 关联测试用例表格分页选项
const casePagination = reactive({
  page: 1,
  pageCount: 1, //总页数
  pageSize: 10 //受控模式下的分页大小
});

// 测试用例显示表格分页选项
const caseViewPagination = reactive({
  pageSize: 5 //受控模式下的分页大小
});

// 测试用例关联表格
const caseColumns = [
  {
    type: 'selection'
  },
  {
    title: 'id',
    key: 'id',
    align: 'center'
  },
  {
    title: '用例名称',
    key: 'name',
    align: 'center'
  }
];

const tempCases = ref([]);
const casesData = ref([]);
let tempArray = [];

function getTempCases(data) {
  data.forEach((v, i) => {
    if (v.manual_cases.length || v.auto_cases.length) {
      v.manual_cases.forEach((c) => {
        tempCases.value.push({
          id: c.id, // 用例ID
          milestoneName: v.milestone.name,
          name: c.name,
          milestoneId: v.milestone.id, // 里程碑ID（任务表）
          type: 'manual',
          status: c.result,
          suite: c.suite,
          taskMilestoneId: v.id, // 里程碑ID（里程碑表）
          usabled: c.usabled
        });
        tempArray[i] = (tempArray[i] || 0) + 1;
      });
      v.auto_cases.forEach((c) => {
        tempCases.value.push({
          id: c.id,
          milestoneName: v.milestone.name,
          name: c.name,
          milestoneId: v.milestone.id,
          type: 'auto',
          status: c.result,
          suite: c.suite,
          usabled: c.usabled
        });
        tempArray[i] = (tempArray[i] || 0) + 1;
      });
    }
  });
}

function getCasesData() {
  let index2 = 0;
  if (tempCases.value) {
    tempCases.value.forEach((v) => {
      let flag = true;
      casesData.value.forEach((t) => {
        if (v.suite === t.suite) {
          t.children.push({
            key: index2++,
            id: v.id,
            taskMilestoneId: v.taskMilestoneId,
            milestoneName: v.milestoneName,
            name: v.name,
            milestoneId: v.milestoneId,
            type: v.type,
            status: v.status,
            suite: v.suite,
            usabled: v.usabled
          });
          flag = false;
        }
      });
      if (flag) {
        casesData.value.push({
          suite: v.suite,
          key: index2++,
          children: [
            {
              key: index2++,
              id: v.id,
              taskMilestoneId: v.taskMilestoneId,
              milestoneName: v.milestoneName,
              name: v.name,
              milestoneId: v.milestoneId,
              type: v.type,
              status: v.status,
              suite: v.suite,
              usabled: v.usabled
            }
          ]
        });
      }
    });
  }
}

//查询用例
function getTaskCases() {
  caseOperator({ is_contain: true })
    .then((res) => {
      [tempCases.value, casesData.value, tempArray] = [[], [], []];
      modalData.value.cases = res.data;
      getTempCases(res.data);
      getCasesData();
    })
    .catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

// 设置里程碑栏所占行数
// function caseRowSpan (rowData, rowIndex) {
//   let count = 0;
//   tempArray.reduce((total, current) => {
//     if (rowIndex === total) {
//       count = current;
//     }
//     return total + current;
//   }, 0);
//   return count;
// }

let tempSearchStr = '';
const suiteId = ref('');
const suiteOptions = ref([]);
let suiteTemp = [];
let tempSuiteId;

// 获取测试套
function getCaseSuite() {
  axios
    .get(`/v1/ws/${workspace.value}/suite`)
    .then((res) => {
      suiteOptions.value = [];
      if (Array.isArray(res.data)) {
        for (const item of res.data) {
          suiteOptions.value.push({
            label: item.name,
            value: item.id
          });
        }
      }
      suiteTemp = suiteOptions.value;
    })
    .catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

// 测试套搜索回调
function suiteHandleSearch(query) {
  if (!query.length) {
    suiteOptions.value = suiteTemp;
    return;
  }
  suiteOptions.value = suiteTemp.filter((item) => ~item.label.indexOf(query));
}

let activeMilestoneId = '';
// 获取测试用例数据
function getCase() {
  loadingRef.value = true;
  caseOperator({
    is_contain: false,
    milestone_id: activeMilestoneId,
    page_num: casePagination.page,
    page_size: casePagination.pageSize,
    case_name: tempSearchStr,
    suite_id: tempSuiteId || null
  })
    .then((res) => {
      loadingRef.value = false;
      casePagination.pageCount = res.data.pages;
      casePagination.pageSize = res.data.page_size;
      caseData.value = res.data.items;
    })
    .catch((err) => {
      loadingRef.value = false;
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}
const caseStr = ref('');

// 查询用例
function queryCase() {
  checkedRowKeys.value = [];
  tempSuiteId = suiteId.value;
  casePagination.page = 1;
  tempSearchStr = caseStr.value;
  getCase();
}
// 删除测试用例
function deleteCase(rowData) {
  caseLoading.value = true;
  if (rowData.children) {
    const allRequest = rowData.children.map((caseItem) => {
      return axios.delete(`/v1/tasks/${modalData.value.detail.id}/milestones/${caseItem.milestoneId}/cases`, {
        case_id: caseItem.id
      });
    });
    Promise.allSettled(allRequest)
      .then(() => {
        caseLoading.value = false;
        getTaskCases();
        initData();
      })
      .catch((err) => {
        caseLoading.value = false;
        window.$message?.error(err.data.error_msg || '未知错误');
      });
  } else {
    axios
      .delete(`/v1/tasks/${modalData.value.detail.id}/milestones/${rowData.milestoneId}/cases`, {
        case_id: rowData.id
      })
      .then(() => {
        caseLoading.value = false;
        getTaskCases();
        initData();
      })
      .catch((err) => {
        caseLoading.value = false;
        window.$message?.error(err.data.error_msg || '未知错误');
      });
  }
}

const showAssociatedCases = ref(false);
const associatedMilestone = ref(null);
const associatedMilestoneOptions = ref([]);

// 显示关联测试弹窗
function addCase(milestoneId) {
  if (milestoneId) {
    if (!suiteOptions.value.length) {
      getCaseSuite();
    }
    showAssociatedCases.value = false;
    showCaseModal.value = true;
    activeMilestoneId = milestoneId;
    getCase();
  } else {
    window.$message?.error('请选择里程碑');
  }
}

function clickAssociatedCases() {
  if (modalData.value.detail.is_single_case && modalData.value.cases.length) {
    window.$message?.error('只允许关联一个测试用例!');
    return;
  }
  if (modalData.value.detail.milestone) {
    addCase(modalData.value.detail.milestone.id);
  } else if (modalData.value.detail.milestones) {
    showAssociatedCases.value = true;
    associatedMilestoneOptions.value = modalData.value.detail.milestones.map((item) => {
      return {
        label: item.name,
        value: item.id
      };
    });
  } else {
    associatedMilestoneOptions.value = [];
    window.$message?.error('请先关联里程碑');
  }
}

const distributeCaseModal = ref(false); // 分配测试用例弹框
const distributeCaseModalData = ref(null); // 分配测试用例弹框数据
const distributeCaseTaskValue = ref(null); // 分配测试用例对应子任务
const distributeCaseOption = ref([]); // 可分配子任务
const distributeAllCases = ref(false); // 分配所有用例或仅分配未完成

const distributeTaskModal = ref(false); // 分配任务弹框
const distributeTaskValue = ref(null); // 分配任务模板
const distributeTaskOption = ref([]); // 可分配模板
const distributeTaskMilestoneValue = ref(null); // 分配任务里程碑
const distributeTaskMilestoneOption = ref([]); // 可分配里程碑

// 获取里程碑选项
function getDistributeMilestone() {
  distributeTaskMilestoneValue.value = null;
  distributeTaskMilestoneOption.value = [];
  if (modalData.value.detail.milestones) {
    modalData.value.detail.milestones.forEach((item) => {
      distributeTaskMilestoneOption.value.push({
        label: item.name,
        value: item.id
      });
    });
  } else if (modalData.value.detail.milestone) {
    distributeTaskMilestoneOption.value.push({
      label: modalData.value.detail.milestone.name,
      value: modalData.value.detail.milestone.id
    });
    distributeTaskMilestoneValue.value = modalData.value.detail.milestone.id;
  }
}

// 取消分配测试用例
function cancelDistributeCase() {
  distributeCaseModal.value = false;
}

// 确认分配测试用例
function distributeCaseBtn(item) {
  if (distributeCaseModalData.value.children) {
    const allRequest = distributeCaseModalData.value.children.map((caseItem) => {
      return axios.put(`/v1/tasks/${modalData.value.detail.id}/milestones/${caseItem.milestoneId}/cases`, {
        cases: [caseItem.id],
        child_task_id: item
      });
    });
    Promise.allSettled(allRequest)
      .then(() => {
        getTaskCases();
        initData();
        distributeCaseModal.value = false;
      })
      .catch((err) => {
        window.$message?.error(err.data.error_msg || '未知错误');
      });
  } else {
    axios
      .put(`/v1/tasks/${modalData.value.detail.id}/milestones/${distributeCaseModalData.value.milestoneId}/cases`, {
        cases: [distributeCaseModalData.value.id],
        child_task_id: item
      })
      .then(() => {
        getTaskCases();
        initData();
        distributeCaseModal.value = false;
      })
      .catch((err) => {
        window.$message?.error(err.data.error_msg || '未知错误');
      });
  }
}

// 取消分配模板
function cancelDistributeTask() {
  distributeTaskModal.value = false;
  distributeTaskValue.value = null;
  distributeTaskOption.value = [];
}

// 确认分配模板
function distributeTaskBtn(value) {
  showDistributeTaskSpin.value = true;
  axios
    .put(`/v1/tasks/${modalData.value.detail.id}/distribute-templates/${value}`, {
      milestone_id: distributeTaskMilestoneValue.value,
      distribute_all_cases: distributeAllCases.value
    })
    .then(() => {
      showDistributeTaskSpin.value = false;
      getTaskCases();
      initData();
      distributeTaskModal.value = false;
      distributeTaskValue.value = null;
      distributeTaskOption.value = [];
    })
    .catch((err) => {
      showDistributeTaskSpin.value = false;
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

const showDistributeTaskSpin = ref(false); // 分配模板加载状态

const caseIssueModalData = ref(null); // 关联用例提单弹框数据
const caseIssueModalRef = ref(null);

// 测试用例显示表格
const caseViewColumns = [
  {
    title: '测试套',
    key: 'suite',
    align: 'left'
  },
  {
    title: '里程碑',
    align: 'center',
    key: 'milestoneName'
    // rowSpan: caseRowSpan
  },
  {
    title: 'id',
    key: 'id',
    align: 'center'
  },
  {
    title: '用例名称',
    align: 'center',
    key: 'name'
  },
  {
    title: '用例类型',
    align: 'center',
    key: 'type',
    render(rowData) {
      let result = '';
      if (rowData.type === 'auto') {
        result = '自动';
      } else if (rowData.type === 'manual') {
        result = '手动';
      }
      return result;
    }
  },
  {
    title: '用例状态',
    align: 'center',
    key: 'status',
    render(rowData) {
      let textColor = '';
      const options = [
        { label: 'running', key: 'running' },
        { label: 'success', key: 'success' },
        { label: 'failed', key: 'failed' }
      ];
      switch (rowData.status) {
        case 'running':
          textColor = 'rgba(0, 47, 167, 1)';
          break;
        case 'success':
          textColor = 'green';
          break;
        case 'failed':
          textColor = 'red';
          break;
        default:
          break;
      }
      const dropDown = h(
        NDropdown,
        {
          trigger: 'click',
          disabled: !editStatus.value || rowData.type === 'auto',
          onSelect: (key) => {
            axios
              .put(`/v1/task/${detailTask.taskId}/milestones/${rowData.taskMilestoneId}/cases/${rowData.id}`, {
                result: key
              })
              .then(() => {
                getTaskCases();
              })
              .catch((err) => {
                window.$message?.error(err.data.error_msg || '未知错误');
              });
          },
          options
        },
        h(
          'span',
          {
            style: `color:${textColor};cursor:pointer`
          },
          rowData.status
        )
      );
      return dropDown;
    }
  },
  {
    title: '可获取',
    align: 'center',
    key: 'available',
    render(rowData) {
      let result = '';
      if (rowData.usabled === true) {
        result = '是';
      } else if (rowData.usabled === false) {
        result = '否';
      }
      return result;
    }
  },
  {
    title: '操作',
    align: 'center',
    key: 'operate',
    render(rowData) {
      if (rowData.suite) {
        return [
          h(
            NButton,
            {
              type: 'primary',
              text: true,
              disabled: !editStatus.value || modalData.value.detail.status_id === 4,
              style: 'margin-right:10px;',
              onClick: () => {
                if (editStatus.value) {
                  distributeCaseModal.value = true;
                  distributeCaseModalData.value = rowData;
                }
              }
            },
            rowData.id !== '' ? '分配' : ''
          ),
          h(
            NButton,
            {
              type: 'primary',
              text: true,
              disabled: !editStatus.value || rowData.status !== 'failed',
              style: 'margin-right:10px;',
              onClick: () => {
                if (editStatus.value) {
                  caseIssueModalRef.value.showModal = true;
                  caseIssueModalData.value = rowData;
                }
              }
            },
            rowData.id !== '' ? '提单' : ''
          ),
          h(
            NButton,
            {
              type: 'primary',
              text: true,
              disabled: !editStatus.value || modalData.value.detail.is_single_case,
              onClick: () => {
                if (editStatus.value) {
                  deleteCase(rowData);
                }
              }
            },
            rowData.id !== '' ? '删除' : ''
          )
        ];
      }
      return null;
    }
  }
];

// 关联父任务选项数组
const associatedTaskOptions = ref([
  {
    label: 'Drive My Car',
    value: 'Drive My Car'
  },
  {
    label: 'Norwegian Wood',
    value: 'Norwegian Wood'
  },
  {
    label: 'Nowhere Man',
    value: 'Nowhere Man'
  }
]);

// 关联子任务选项数组
const associatedChildTaskOptions = ref([
  {
    label: 'Drive My Car',
    value: 'Drive My Car'
  },
  {
    label: 'Norwegian Wood',
    value: 'Norwegian Wood'
  },
  {
    label: 'Nowhere Man',
    value: 'Nowhere Man'
  }
]);

// 父任务数组
const fatherTaskArray = ref([
  {
    label: 'abcd',
    value: 'abcd'
  },
  {
    label: 'abea',
    value: 'abea'
  },
  {
    label: 'baed',
    value: 'baed'
  },
  {
    label: 'bbaa',
    value: 'bbaa'
  }
]);

function getMdFiles() {
  axios
    .get(`/v1/tasks/${detailTask.taskId}/reports`)
    .then((res) => {
      if (res.data?.title || res.data?.content) {
        modalData.value.reportArray = [{ title: res.data.title || '', content: res.data.content || '' }];
      } else {
        modalData.value.reportArray = [];
      }
    })
    .catch((error) => {
      window.$message?.error(error.data.error_msg || '未知错误');
    });
}

let timer; // 父子任务搜索防抖

function transTaskType(type) {
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

// 合并父子任务；获取分配子任务列表
function mergeFamilyTask(response) {
  modalData.value.relationFatherTask = response.data.parents.map((item) => {
    return {
      id: item.id,
      relation: '父任务',
      taskName: item.title,
      taskType: transTaskType(item.type),
      belongTo: item.belong.user_name ? item.belong.user_name : item.belong.name,
      executor: item.executor.user_name,
      startTime: formatTime(item.start_time, 'yyyy-MM-dd hh:mm:ss'),
      endTime: formatTime(item.deadline, 'yyyy-MM-dd hh:mm:ss'),
      status: item.status.name
    };
  });

  modalData.value.relationChildTask = response.data.children.map((item) => {
    return {
      id: item.id,
      relation: '子任务',
      taskName: item.title,
      taskType: transTaskType(item.type),
      belongTo: item.belong.user_name ? item.belong.user_name : item.belong.name,
      executor: item.executor.user_name,
      startTime: formatTime(item.start_time, 'yyyy-MM-dd hh:mm:ss'),
      endTime: formatTime(item.deadline, 'yyyy-MM-dd hh:mm:ss'),
      status: item.status.name
    };
  });

  distributeCaseOption.value = response.data.children.map((item) => {
    return {
      label: item.title,
      value: item.id
    };
  });

  return [...modalData.value.relationFatherTask, ...modalData.value.relationChildTask];
}

// 点击任务获取任务详情
function getDetail(detailData) {
  detailTask.taskId = detailData.id;
  detailTask.level = detailData.level;
  getDetailTask().then(() => {
    getTaskHelper();
    getTaskComment();
    getTaskCases();
    getMdFiles();
    familyTaskOperator({ not_in: false }).then((response) => {
      modalData.value.relationTask = mergeFamilyTask(response);
    });
  });
}

// 编辑任务选项
function editTask(id, editInfo) {
  showLoading.value = true;
  axios
    .put(`/v1/tasks/${id}`, editInfo)
    .then(() => {
      showLoading.value = false;
      initData();
      if (!Object.keys(editInfo).includes('is_delete')) {
        getDetailTask().then(() => {
          getTaskCases();
        });
      }
    })
    .catch((err) => {
      showLoading.value = false;
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

// 编辑任务选项
function editTaskExecutor(id, editInfo) {
  showLoading.value = true;
  axios
    .put(`/v1/tasks/${id}/executor`, editInfo)
    .then(() => {
      showLoading.value = false;
      initData();
      if (!Object.keys(editInfo).includes('is_delete')) {
        getDetailTask();
      }
    })
    .catch((err) => {
      showLoading.value = false;
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

// 测试用例表格行id设置
function caseRowKey(row) {
  return row.id;
}

// 测试用例页码变更
function handleCasePageChange(currentPage) {
  if (!loadingRef.value) {
    casePagination.page = currentPage;
    getCase();
  }
}

// 取消关联测试用例
function cancelCaseBtn() {
  checkedRowKeys.value = [];
  showCaseModal.value = false;
}

// 新增关联用例
function addTaskCase() {
  axios
    .post(`/v1/tasks/${modalData.value.detail.id}/milestones/${activeMilestoneId}/cases`, {
      case_id: checkedRowKeys.value
    })
    .then(() => {
      checkedRowKeys.value = [];
      getTaskCases();
      getCase();
      initData();
      window.$message?.success('用例关联成功!');
      showCaseModal.value = false;
    })
    .catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

// 关联测试用例按钮
function addCaseBtn() {
  // handleCase('add', checkedRowKeys.value);
  addTaskCase();
}

// 跳转子任务
function jumpChildTask(jumpTask) {
  detailTask.taskId = jumpTask.id;
  detailTask.level = jumpTask.level;
  detailTask.parentId = jumpTask.parent_id;
  getDetailTask().then(() => {
    getTaskHelper();
    getTaskComment();
  });
  showBackMenu.value = true;
}

// 显示关联父任务
function associatedTask() {
  showAssociatedTask.value = false;
}

// 取消关联父任务
function cancelAssociatedTask() {
  fatherTaskArrayTemp.value = [];
  showAssociatedTask.value = true;
}

// 关联任务
function relationTask(option) {
  return new Promise((resolve, reject) => {
    axios
      .post(`/v1/tasks/${modalData.value.detail.id}/family`, option)
      .then((res) => {
        resolve(res);
      })
      .catch((err) => {
        reject(err);
      });
  });
}

// 确认关联父任务
function associatedTaskBtn(value) {
  if (modalData.value.detail.milestone || modalData.value.detail.milestones) {
    relationTask({ parent_id: value }).then(() => {
      familyTaskOperator({ not_in: false }).then((response) => {
        modalData.value.relationTask = mergeFamilyTask(response);
        cancelAssociatedTask();
      });
      getTask();
    });
  } else {
    window.$message?.error('请先关联里程碑');
  }
}

// 取消关联任务
function editRelationTask(option) {
  axios
    .delete(`/v1/tasks/${modalData.value.detail.id}/family`, option)
    .then(() => {
      initData();
      familyTaskOperator({ not_in: false }).then((response) => {
        modalData.value.relationTask = mergeFamilyTask(response);
      });
    })
    .catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

// 显示关联子任务
function associatedChildTask() {
  showAssociatedChildTask.value = false;
}

// 取消关联子任务
function cancelAssociatedChildTask() {
  childTaskArrayTemp.value = [];
  showAssociatedChildTask.value = true;
}

// 确认关联子任务
function associatedChildTaskBtn(value) {
  if (modalData.value.detail.milestone || modalData.value.detail.milestones) {
    relationTask({ child_id: value })
      .then(() => {
        familyTaskOperator({ not_in: false }).then((response) => {
          modalData.value.relationTask = mergeFamilyTask(response);
          initData();
          cancelAssociatedChildTask();
        });
      })
      .catch((err) => {
        window.$message?.error(err.data.error_msg || '未知错误');
      });
  } else {
    window.$message?.error('请先关联里程碑');
  }
}

// 关联父任务选择框搜索
function handleSearchFatherTask(query) {
  fatherTaskLoading.value = true;
  if (timer) {
    clearTimeout(timer);
  }
  timer = setTimeout(() => {
    familyTaskOperator({ not_in: true, is_parent: true, title: query }).then((res) => {
      fatherTaskArrayTemp.value = res.data.map((item) => {
        return {
          label: item.title,
          value: item.id
        };
      });
    });
  }, 1000);
}

// 聚焦关联父任务选择框回调
function handleFocusFatherTask() {
  handleSearchFatherTask();
}

// 关联子任务选择框搜索
function handleSearchChildTask(query) {
  childTaskLoading.value = true;
  if (timer) {
    clearTimeout(timer);
  }
  timer = setTimeout(() => {
    familyTaskOperator({ not_in: true, is_parent: false, title: query }).then((res) => {
      childTaskArrayTemp.value = res.data.map((item) => {
        return {
          label: item.title,
          value: item.id
        };
      });
    });
  }, 1000);
}

// 聚焦子任务搜索回调
function handleFocusChildTask() {
  handleSearchChildTask();
}

const familyColumns = ref([
  {
    title: '任务名称',
    key: 'taskName',
    align: 'center'
  },
  {
    title: '关联',
    key: 'relation',
    align: 'center'
  },
  {
    title: '任务类型',
    key: 'taskType',
    align: 'center'
  },
  {
    title: '归属',
    key: 'belongTo',
    align: 'center'
  },
  {
    title: '责任人',
    key: 'executor',
    align: 'center'
  },
  {
    title: '开始时间',
    key: 'startTime',
    align: 'center'
  },
  {
    title: '截止时间',
    key: 'endTime',
    align: 'center'
  },
  {
    title: '当前状态',
    key: 'status',
    align: 'center'
  },
  {
    title: '操作',
    key: 'operation',
    align: 'center',
    render(row) {
      return h(
        NButton,
        {
          type: 'primary',
          text: true,
          style: '',
          disabled: !editStatus.value,
          onClick: (e) => {
            e.stopPropagation();
            const d = window.$dialog?.warning({
              title: '取消关联',
              content: '您确定要取消关联此任务吗？',
              action: () => {
                const confirmBtn = h(
                  NButton,
                  {
                    type: 'info',
                    ghost: true,
                    onClick: () => {
                      if (row.relation === '父任务') {
                        editRelationTask({ parent_id: row.id });
                      } else {
                        editRelationTask({ child_id: row.id });
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
        },
        '取消关联'
      );
    }
  }
]);

function familyRowProps(rowData) {
  return {
    style: 'cursor: pointer;',
    onClick: () => {
      showModal.value = false;
      window.setTimeout(() => {
        getDetail(rowData);
      }, 300);
    }
  };
}

// 拖动任务改变状态
function changeStatus($event, status) {
  axios
    .put(`/v1/tasks/${$event.id}`, { status_id: status.id })
    .then(() => {
      showLoading.value = false;
      if ($event.has_auto_case && status.id === 3) {
        window.$message?.success('该任务的自动化测试用例已经开始执行');
      }
      $event.status.name = status.statusItem;
    })
    .catch((err) => {
      showLoading.value = false;
      window.$message?.error(err.data.error_msg || '未知错误');
      initData();
    });
}

function getTemplateName() {
  distributeTaskValue.value = null;
  distributeTaskOption.value = [];
  axios
    .get('v1/tasks/distribute-templates', {
      group_id: modalData.value.detail.group_id
    })
    .then((res) => {
      if (res.data.items) {
        res.data.items.forEach((item) => {
          distributeTaskOption.value.push({
            label: item.name,
            value: item.id
          });
        });
      }
    })
    .catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

// 任务详情右上角菜单选择：删除任务、生成报告
function handleSelect(key) {
  if (key === 'deleteTask') {
    const d = window.$dialog?.warning({
      title: '删除任务',
      content: '您确定要删除此任务吗？',
      action: () => {
        const confirmBtn = h(
          NButton,
          {
            type: 'info',
            ghost: true,
            onClick: () => {
              editTask(modalData.value.detail.id, { is_delete: true });
              showModal.value = false;
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
  } else if (key === 'reporting') {
    generateMdFile(modalData.value.detail.id, modalData.value.detail.type === 'VERSION');
  } else if (key === 'distributeTask') {
    distributeTaskModal.value = true;
    getTemplateName();
    getDistributeMilestone();
  }
}

// 关闭遮罩按钮
function closeModal() {
  showModal.value = false;
}

// 任务名称显示/编辑切换
function showTitleInput() {
  if (showTaskTitleInput.value === false) {
    if (editStatus.value) {
      showTaskTitleInput.value = true;
      taskName.value = modalData.value.detail.title;
      nextTick(() => {
        titleInputRef.value.focus();
      });
    }
  } else {
    showTaskTitleInput.value = false;
    if (taskName.value.trim() !== '') {
      editTask(modalData.value.detail.id, { title: taskName.value });
    }
  }
}

// 任务详情页关闭回调
function leaveModal() {
  showBackMenu.value = false;
  editStatus.value = false;
  showEditTaskDetailBtn.value = true;
  showAssociatedTask.value = true;
  showAssociatedChildTask.value = true;
  showAssociatedCases.value = false;
}

// 添加子任务
function createChildTask() {
  store.commit('taskManage/toggleNewTaskDrawer');
  detailTask.statusId = modalData.value.detail.status_id;
  showRelation.value = false;
  model.value.fatherTask = [modalData.value.detail.id];
  createTask();
}

// 发表评论
function commentFn(str) {
  if (str) {
    showLoading.value = true;
    axios
      .post(`/v1/tasks/${modalData.value.detail.id}/comment`, {
        content: str
      })
      .then(() => {
        getTaskComment();
        showLoading.value = false;
        commentInput.value = '';
      })
      .catch((err) => {
        window.$message?.error(err.data.error_msg || '未知错误');
        showLoading.value = false;
      });
  }
}

// 返回父任务
function jumpBack(data) {
  detailTask.level = data.level - 1;
  detailTask.taskId = detailTask.parentId;
  getDetailTask().then(() => {
    getTaskHelper();
    getTaskComment();
  });
  detailTask.level === 1 ? (showBackMenu.value = false) : (showBackMenu.value = true);
}

// 任务详情页改变状态回调
function statusChange(value) {
  editTask(modalData.value.detail.id, { status_id: value });
}

// 任务详情页执行机架构改变回调
function frameChange(value) {
  editTask(modalData.value.detail.id, { frame: value });
}

// 选择协助人
function getHelper(value) {
  showPopoverHelper.value = false;
  const data = [];
  for (const item of value) {
    try {
      const element = JSON.parse(item);
      data.push({ participant_id: element.id, type: element.type });
    } catch (error) {
      console.log(error);
    }
  }
  axios
    .put(`/v1/tasks/${modalData.value.detail.id}/participants`, {
      participants: data
    })
    .then(() => {
      // initData();
      getTaskHelper();
    })
    .catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

// 选择里程碑
function getMilepost(value) {
  showMilepost.value = false;
  editTask(modalData.value.detail.id, { milestone_id: value.id });
}

// 组织任务获取里程碑数组
function getMileposts(groupValue) {
  editTask(modalData.value.detail.id, { milestones: groupValue });
  showMilepost.value = false;
}

// 设置截止时间
function updateClosingTime(value) {
  editTask(modalData.value.detail.id, {
    deadline: formatTime(value, 'yyyy-MM-dd hh:mm:ss')
  });
}

// 切换内容选项编辑/显示模式
function showContent() {
  if (showContentInput.value === false) {
    if (editStatus.value) {
      showContentInput.value = true;
      nextTick(() => {
        contentInputRef.value.focus();
      });
    }
  } else {
    showContentInput.value = false;
    editTask(modalData.value.detail.id, {
      content: modalData.value.detail.content
    });
  }
}

// 切换显示内容：关联用例 评论 关联任务
function toggleContent(option) {
  showFooterContent.value = option;
}

// 获取责任人
function getExecutors(value) {
  showPopoverExecutors.value = false;
  const options = {};
  options.executor_id = value.id;
  options.executor_type = value.type;
  editTaskExecutor(modalData.value.detail.id, options);
}

// 获取责任人
function getExecutor(value, type) {
  showPopoverExecutor.value = false;
  const options = {};
  if (type === 'ORGANIZATION') {
    options.executor_id = value.id;
    options.executor_type = value.type;
  } else if (type === 'GROUP') {
    options.group_id = modalData.value.detail.group_id;
    options.executor_id = value.id;
  } else if (type === 'VERSION') {
    options.executor_id = value.id;
    options.executor_type = value.type;
  }
  editTaskExecutor(modalData.value.detail.id, options);
}

function showReport(file) {
  md.name = file.title;
  md.content = file.content;
  md.taskId = modalData.value.detail.id;
  showReportModal.value = true;
}

// 编辑任务详情
function editTaskDetail() {
  if (showEditTaskDetailBtn.value) {
    if (editRole.value) {
      window.$message?.success('进入编辑模式');
      editStatus.value = true;
      showEditTaskDetailBtn.value = false;
    } else {
      window.$message?.error('无编辑权限');
    }
  } else {
    window.$message?.success('退出编辑模式');
    showEditTaskDetailBtn.value = true;
    editStatus.value = false;
  }
}

// 自动完成
const autocompleteArray = ref([
  {
    label: '是',
    value: true
  },
  {
    label: '否',
    value: false
  }
]);

// 任务详情页自动完成变回调
function autocompleteChange(value) {
  editTask(modalData.value.detail.id, { automatic_finish: value });
}
function changeManage(value) {
  editTask(modalData.value.detail.id, { is_manage_task: value });
}
function getFrame() {
  axios.get('/v1/task/frame').then((res) => {
    frameArray.value = res.data.map((item) => ({ label: item, value: item }));
  });
}

export {
  getFrame,
  autocompleteArray,
  autocompleteChange,
  init,
  tempCases,
  reportArray,
  showModal,
  showCaseModal,
  modalData,
  showTaskTitleInput,
  showBackMenu,
  titleInputRef,
  showPopoverExecutor,
  showPopoverExecutors,
  showPopoverHelper,
  showMilepost,
  showClosingTime,
  showContentInput,
  showFooterContent,
  contentInputRef,
  commentInput,
  taskName,
  checkedRowKeys,
  loadingRef,
  caseData,
  caseLoading,
  hasFatherTask,
  hasChildTask,
  showAssociatedTask,
  showAssociatedChildTask,
  associatedTaskValue,
  associatedChildTaskValue,
  childTaskArray,
  showLoading,
  detailTask,
  casePagination,
  caseViewPagination,
  caseColumns,
  caseViewColumns,
  menuOptions,
  suiteId,
  associatedTaskOptions,
  associatedChildTaskOptions,
  fatherTaskArray,
  editRole,
  fatherTaskArrayTemp,
  childTaskArrayTemp,
  fatherTaskLoading,
  childTaskLoading,
  caseStr,
  editStatus,
  showEditTaskDetailBtn,
  frameArray,
  suiteOptions,
  queryCase,
  getDetailTask,
  getDetail,
  editTask,
  editTaskExecutor,
  caseRowKey,
  getCase,
  handleCasePageChange,
  addCase,
  cancelCaseBtn,
  addCaseBtn,
  jumpChildTask,
  associatedTask,
  cancelAssociatedTask,
  associatedTaskBtn,
  relationTask,
  editRelationTask,
  associatedChildTask,
  cancelAssociatedChildTask,
  associatedChildTaskBtn,
  handleSearchFatherTask,
  handleFocusFatherTask,
  handleSearchChildTask,
  handleFocusChildTask,
  familyTaskOperator,
  changeStatus,
  handleSelect,
  closeModal,
  showTitleInput,
  leaveModal,
  createChildTask,
  commentFn,
  jumpBack,
  statusChange,
  frameChange,
  getHelper,
  getMilepost,
  getMileposts,
  updateClosingTime,
  showContent,
  toggleContent,
  getExecutors,
  getExecutor,
  renderIcon,
  formatTime,
  showReport,
  editTaskDetail,
  showReportModal,
  tinymce,
  suiteHandleSearch,
  familyColumns,
  familyRowProps,
  getMdFiles,
  distributeCaseModal,
  distributeCaseTaskValue,
  cancelDistributeCase,
  distributeCaseBtn,
  distributeCaseOption,
  distributeCaseModalData,
  casesData,
  showAssociatedCases,
  associatedMilestone,
  associatedMilestoneOptions,
  clickAssociatedCases,
  distributeTaskModal,
  distributeTaskValue,
  distributeTaskOption,
  cancelDistributeTask,
  distributeTaskBtn,
  distributeTaskMilestoneValue,
  distributeTaskMilestoneOption,
  getDistributeMilestone,
  distributeAllCases,
  changeManage,
  caseIssueModalData,
  caseIssueModalRef,
  showDistributeTaskSpin
};
