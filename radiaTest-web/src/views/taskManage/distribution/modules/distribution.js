import { NButton } from 'naive-ui';
import { ref, h, reactive } from 'vue';
import axios from '@/axios';
import { formatTime } from '@/assets/utils/dateFormatUtils.js';
// import { storage } from '@/assets/utils/storageUtils';

const showNewTemplateDrawer = ref(false);
const distributionTableData = ref([]);
const templateFormRef = ref(null);
const drawerTitle = ref(null);
const drawerType = ref(null);

const drawerRules = ref({
  templateName: {
    required: true,
    message: '模板名称必填',
    trigger: ['blur', 'input'],
  },
  groupName: {
    type: 'number',
    required: true,
    message: '请选择团队',
    trigger: ['blur', 'change'],
  },
  templateType: {
    required: true,
    message: '模板类型必填',
    trigger: ['blur', 'input'],
  },
  executor: {
    type: 'number',
    required: true,
    message: '请选择责任人',
    trigger: ['blur', 'change'],
  },
});
const drawerModel = ref({
  templateName: null,
  templateType: null,
  groupName: null,
  suiteNames: null,
  executor: null,
  helpers: null,
});

const groupNameOptions = ref([]);
const groupSelectLoading = ref(false);

function getGroupAxios() {
  groupNameOptions.value = [];
  groupSelectLoading.value = true;
  axios
    .get('/v1/groups', {
      page_num: 1,
      page_size: 99999999,
    })
    .then((res) => {
      groupSelectLoading.value = false;
      if (res.data.items) {
        res.data.items.forEach((item) => {
          groupNameOptions.value.push({
            label: item.name,
            value: item.id,
          });
        });
      }
    })
    .catch((err) => {
      groupSelectLoading.value = false;
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

const helpersOptions = ref([]);
let helpersTemp = [];
const executorOptions = ref([]);
let executorTemp = [];
const userSelectLoading = ref(false);

function getUserAxios() {
  userSelectLoading.value = true;
  helpersOptions.value = [];
  helpersTemp = [];
  executorOptions.value = [];
  executorTemp = [];
  axios
    .get(`/v1/groups/${drawerModel.value.groupName}/users`, {
      page_num: 1,
      page_size: 99999999,
    })
    .then((res) => {
      userSelectLoading.value = false;
      if (res.data.items) {
        res.data.items.forEach((item) => {
          helpersOptions.value.push({
            label: item.gitee_name,
            value: item.gitee_id,
          });
        });
        helpersTemp = helpersOptions.value;
        executorTemp = helpersOptions.value;
        executorOptions.value = helpersOptions.value;
      }
    })
    .catch((err) => {
      userSelectLoading.value = false;
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

const suiteNamesOptions = ref([]);
let suitesTemp = [];
const suiteSelectLoading = ref(false);

function getSuitesAxios() {
  suiteSelectLoading.value = true;
  suiteNamesOptions.value = [];
  suitesTemp = [];
  axios
    .get('/v1/tasks/distribute_templates/suites', {
      page_num: 1,
      page_size: 99999999,
    })
    .then((res) => {
      suiteSelectLoading.value = false;
      if (res.data.items) {
        res.data.items.forEach((item) => {
          suiteNamesOptions.value.push({
            label: item.name,
            value: item.id,
          });
        });
        suitesTemp = suiteNamesOptions.value;
      }
    })
    .catch((err) => {
      suiteSelectLoading.value = false;
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

function handleSuiteNamesSearch(query) {
  if (!query.length) {
    suiteNamesOptions.value = suitesTemp;
    return;
  }
  suiteNamesOptions.value = suitesTemp.filter(
    (item) => ~item.label.indexOf(query)
  );
}

function handleChangeGroup(value) {
  drawerModel.value.groupName = value;
  drawerModel.value.executor = null;
  drawerModel.value.helpers = [];
  helpersOptions.value = [];
  helpersTemp = [];
  executorOptions.value = [];
  executorTemp = [];
  axios
    .get(`/v1/groups/${value}/users`, { page_num: 1, page_size: 99999999 })
    .then((res) => {
      if (res.data.items) {
        res.data.items.forEach((item) => {
          helpersOptions.value.push({
            label: item.gitee_name,
            value: item.gitee_id,
          });
        });
        helpersTemp = helpersOptions.value;
        executorTemp = helpersOptions.value;
        executorOptions.value = helpersOptions.value;
      }
    })
    .catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

function handleHelpersSearch(query) {
  if (!query.length) {
    helpersOptions.value = helpersTemp;
    return;
  }
  helpersOptions.value = helpersTemp.filter(
    (item) => ~item.label.indexOf(query)
  );
}

function handleExecutorSearch(query) {
  if (!query.length) {
    executorOptions.value = executorTemp;
    return;
  }
  executorOptions.value = executorTemp.filter(
    (item) => ~item.label.indexOf(query)
  );
}

function handleChangeExecutor(v) {
  helpersOptions.value = [];
  helpersTemp = [];
  axios
    .get(`/v1/groups/${drawerModel.value.groupName}/users`, {
      except_list: v,
      page_num: 1,
      page_size: 99999999,
    })
    .then((res) => {
      if (res.data.items) {
        res.data.items.forEach((item) => {
          helpersOptions.value.push({
            label: item.gitee_name,
            value: item.gitee_id,
          });
        });
        helpersTemp = helpersOptions.value;
      }
    })
    .catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

function handleChangeHelper(v) {
  executorOptions.value = [];
  executorTemp = [];
  axios
    .get(`/v1/groups/${drawerModel.value.groupName}/users`, {
      except_list: v.join(','),
      page_num: 1,
      page_size: 99999999,
    })
    .then((res) => {
      if (res.data.items) {
        res.data.items.forEach((item) => {
          executorOptions.value.push({
            label: item.gitee_name,
            value: item.gitee_id,
          });
        });
        executorTemp = helpersOptions.value;
      }
    })
    .catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

// 抽屉打开回调
function drawerShowCb(type) {
  showNewTemplateDrawer.value = true;
  switch (type) {
    case 'newTemplate':
      drawerTitle.value = '创建模板';
      break;
    case 'newTemplateType':
      drawerTitle.value = '新增类型';
      break;
    case 'editTemplateName':
      drawerTitle.value = '修改模板名称';
      break;
    case 'editTemplateType':
      drawerTitle.value = '修改类型信息';
      break;
    default:
      drawerTitle.value = '';
  }
}

function drawerTypeJudge() {
  return (
    drawerType.value === 'newTemplateType' ||
    drawerType.value === 'editTemplateType'
  );
}

const distributionLoading = ref(false);
const templatePagination = reactive({
  page: 1,
  pageCount: 1, //总页数
  pageSize: 15, //受控模式下的分页大小
});

function getTemplateTableRowsData(items) {
  let index = 0;
  items.forEach((item, i) => {
    distributionTableData.value.push({
      key: index++,
      level: 'templateName',
      templateNameID: item.id,
      templateName: item.name,
      groupID: item.group.id,
      group: item.group.name,
    });
    if (item.types) {
      distributionTableData.value[i].children = [];
      item.types.forEach((type, j) => {
        let helpers = type.helpers.map((helper) => helper.gitee_name).join(',');
        distributionTableData.value[i].children.push({
          key: index++,
          level: 'templateType',
          templateNameID: item.id,
          templateName: item.name,
          templateTypeID: type.id,
          templateType: type.name,
          groupID: item.group.id,
          group: item.group.name,
          creator: type.creator.gitee_name,
          executor: type.executor.gitee_name,
          helper: helpers,
          creatingTime: formatTime(type.create_time, 'yyyy-MM-dd hh:mm:ss'),
        });
        if (type.suites) {
          distributionTableData.value[i].children[j].children = [];
          type.suites.forEach((suite) => {
            distributionTableData.value[i].children[j].children.push({
              key: index++,
              level: 'suiteName',
              templateName: item.name,
              templateType: type.name,
              suiteName: suite.name,
              group: item.group.name,
              creator: type.creator.gitee_name,
              executor: type.executor.gitee_name,
              helper: helpers,
              creatingTime: formatTime(type.create_time, 'yyyy-MM-dd hh:mm:ss'),
            });
          });
        }
      });
    }
  });
}

// 获取模板表格数据
function getTemplateTableData() {
  distributionLoading.value = true;
  axios
    .get('v1/tasks/distribute_templates', {
      page_num: templatePagination.page,
      page_size: templatePagination.pageSize,
    })
    .then((res) => {
      distributionLoading.value = false;
      distributionTableData.value = [];
      templatePagination.pageCount = res.data.pages;
      templatePagination.pageSize = res.data.page_size;
      if (res.data.items) {
        getTemplateTableRowsData(res.data.items);
      }
    })
    .catch((err) => {
      distributionLoading.value = false;
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

function handleTemplatePageChange(currentPage) {
  if (!distributionLoading.value) {
    templatePagination.page = currentPage;
    getTemplateTableData();
  }
}

function deleteTemplateName(templateNameID) {
  axios
    .delete(`/v1/tasks/distribute_templates/${templateNameID}`)
    .then(() => {
      getTemplateTableData();
    })
    .catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

function deleteTemplateType(templateTypeID) {
  axios
    .delete(`/v1/tasks/distribute_templates/types/${templateTypeID}`)
    .then(() => {
      getTemplateTableData();
    })
    .catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

function warning(title, content, confirmCb, cancelCb) {
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
            d.destroy();
            if (confirmCb) {
              confirmCb();
            }
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
            if (cancelCb) {
              cancelCb();
            }
          },
        },
        '取消'
      );
      return [cancelmBtn, confirmBtn];
    },
  });
}

// 获取模板类型数据
function getTemplateType(value) {
  drawerModel.value.suiteNames = [];
  drawerModel.value.executor = null;
  drawerModel.value.helpers = [];
  axios
    .get(
      `v1/tasks/distribute_templates/suites?page_num=1&page_size=99999999&type_id=${value}`
    )
    .then((res) => {
      if (res.data.suites) {
        res.data.suites.forEach((item) => {
          drawerModel.value.suiteNames.push(item.id);
        });
      }
      drawerModel.value.executor = res.data.executor.gitee_id;
      if (res.data.helpers) {
        res.data.helpers.forEach((item) => {
          drawerModel.value.helpers.push(item.gitee_id);
        });
      }
      handleChangeExecutor(drawerModel.value.executor);
      handleChangeHelper(drawerModel.value.helpers);
      getGroupAxios();
      getSuitesAxios();
    })
    .catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

// 新增类型
function operateMenuAdd(rowData) {
  return h(
    NButton,
    {
      type: 'primary',
      text: true,
      style: '',
      onClick: () => {
        drawerModel.value.templateName = rowData.templateName;
        drawerModel.value.templateNameID = rowData.templateNameID;
        drawerModel.value.groupName = rowData.groupID;
        drawerType.value = 'newTemplateType';
        drawerShowCb(drawerType.value);
        getUserAxios();
        getGroupAxios();
        getSuitesAxios();
      },
    },
    '新增'
  );
}

// 修改菜单
function operateMenuEdit(rowData) {
  return h(
    NButton,
    {
      type: 'primary',
      text: true,
      style: 'margin-left:10px;',
      onClick: () => {
        if (rowData.level === 'templateName') {
          drawerModel.value.templateNameID = rowData.templateNameID;
          drawerModel.value.templateName = rowData.templateName;
          drawerType.value = 'editTemplateName';
          drawerShowCb(drawerType.value);
        } else if (rowData.level === 'templateType') {
          drawerModel.value.templateName = rowData.templateName;
          drawerModel.value.groupName = rowData.groupID;
          drawerModel.value.templateTypeID = rowData.templateTypeID;
          drawerModel.value.templateType = rowData.templateType;
          drawerType.value = 'editTemplateType';
          drawerShowCb(drawerType.value);
          getTemplateType(rowData.templateTypeID);
        }
      },
    },
    '修改'
  );
}

// 删除菜单
function operateMenuDelete(rowData) {
  return h(
    NButton,
    {
      type: 'primary',
      text: true,
      style: 'margin-left:10px;',
      onClick: () => {
        if (rowData.level === 'templateName') {
          warning('删除模板', '您确定要删除此模板吗？', () =>
            deleteTemplateName(rowData.templateNameID)
          );
        } else if (rowData.level === 'templateType') {
          warning('删除模板类型', '您确定要删除此模板类型吗？', () =>
            deleteTemplateType(rowData.templateTypeID)
          );
        }
      },
    },
    '删除'
  );
}

const distributionColumns = [
  {
    title: '模板名称',
    key: 'templateName',
    align: 'left',
  },
  {
    title: '团队',
    key: 'group',
    align: 'center',
  },
  {
    title: '模板类型',
    key: 'templateType',
    align: 'center',
  },
  {
    title: '测试套',
    key: 'suiteName',
    align: 'center',
  },
  {
    title: '创建人',
    key: 'creator',
    align: 'center',
  },
  {
    title: '责任人',
    key: 'executor',
    align: 'center',
  },
  {
    title: '协助人',
    key: 'helper',
    align: 'center',
  },
  {
    title: '创建日期',
    key: 'creatingTime',
    align: 'center',
  },
  {
    title: '操作',
    key: 'operate',
    align: 'center',
    render(rowData) {
      if (rowData.level === 'templateName') {
        return [
          operateMenuAdd(rowData),
          operateMenuEdit(rowData),
          operateMenuDelete(rowData),
        ];
      } else if (rowData.level !== 'suiteName') {
        return [operateMenuEdit(rowData), operateMenuDelete(rowData)];
      }
      return null;
    },
  },
];

// 点击“创建模板”按钮
function showAddTemplateBtn() {
  drawerType.value = 'newTemplate';
  drawerShowCb(drawerType.value);
  getGroupAxios();
}

// 取消创建模板
function cancelCreateTemplate() {
  showNewTemplateDrawer.value = false;
  drawerModel.value = {};
  helpersOptions.value = [];
  executorOptions.value = [];
  helpersTemp = [];
  executorTemp = [];
}

// “创建模板”按钮
function createTemplate() {
  templateFormRef.value.validate((error) => {
    if (error) {
      window.$message?.error('请填写相关信息');
    } else {
      axios
        .post('/v1/tasks/distribute_templates', {
          name: drawerModel.value.templateName,
          group_id: drawerModel.value.groupName,
        })
        .then(() => {
          getTemplateTableData();
          showNewTemplateDrawer.value = false;
          drawerModel.value = {};
        })
        .catch((err) => {
          window.$message?.error(err.data.error_msg || '未知错误');
        });
    }
  });
}

// “新增类型”按钮
function createTemplateType() {
  templateFormRef.value.validate((error) => {
    if (error) {
      window.$message?.error('请填写相关信息');
    } else {
      axios
        .post(
          `/v1/tasks/distribute_templates/${drawerModel.value.templateNameID}/types`,
          {
            name: drawerModel.value.templateType,
            executor_id: drawerModel.value.executor,
            suites: drawerModel.value.suiteNames,
            helpers: drawerModel.value.helpers,
          }
        )
        .then(() => {
          getTemplateTableData();
          showNewTemplateDrawer.value = false;
          drawerModel.value = {};
        })
        .catch((err) => {
          window.$message?.error(err.data.error_msg || '未知错误');
        });
    }
  });
}

// 修改模板名称回调
function editTemplateNameCb() {
  templateFormRef.value.validate((error) => {
    if (error) {
      window.$message?.error('请填写相关信息');
    } else {
      axios
        .put(
          `/v1/tasks/distribute_templates/${drawerModel.value.templateNameID}`,
          {
            name: drawerModel.value.templateName,
          }
        )
        .then(() => {
          getTemplateTableData();
          showNewTemplateDrawer.value = false;
          drawerModel.value = {};
        })
        .catch((err) => {
          window.$message?.error(err.data.error_msg || '未知错误');
        });
    }
  });
}

// 修改模板类型数据回调
function editTemplateTypeCb() {
  templateFormRef.value.validate((error) => {
    if (error) {
      window.$message?.error('请填写相关信息');
    } else {
      axios
        .put(
          `/v1/tasks/distribute_templates/types/${drawerModel.value.templateTypeID}`,
          {
            name: drawerModel.value.templateType,
            executor_id: drawerModel.value.executor,
            suites: drawerModel.value.suiteNames,
            helpers: drawerModel.value.helpers,
          }
        )
        .then(() => {
          getTemplateTableData();
          showNewTemplateDrawer.value = false;
          drawerModel.value = {};
        })
        .catch((err) => {
          window.$message?.error(err.data.error_msg || '未知错误');
        });
    }
  });
}

function init() {
  getTemplateTableData();
}

export {
  distributionLoading,
  distributionColumns,
  distributionTableData,
  showAddTemplateBtn,
  showNewTemplateDrawer,
  drawerModel,
  drawerRules,
  executorOptions,
  cancelCreateTemplate,
  createTemplate,
  init,
  templatePagination,
  getTemplateTableData,
  suiteNamesOptions,
  handleSuiteNamesSearch,
  helpersOptions,
  handleHelpersSearch,
  handleExecutorSearch,
  templateFormRef,
  createTemplateType,
  groupNameOptions,
  handleChangeGroup,
  drawerTitle,
  drawerType,
  editTemplateNameCb,
  editTemplateTypeCb,
  handleChangeExecutor,
  handleChangeHelper,
  handleTemplatePageChange,
  drawerTypeJudge,
  groupSelectLoading,
  userSelectLoading,
  suiteSelectLoading,
};
