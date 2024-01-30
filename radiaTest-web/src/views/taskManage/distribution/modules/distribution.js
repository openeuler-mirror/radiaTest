import { NButton } from 'naive-ui';
import { ref, h, reactive } from 'vue';
import axios from '@/axios';
import { formatTime } from '@/assets/utils/dateFormatUtils.js';
import { getGroup, getCaseSetNodes, getCaseNode, getDistributeTemplates, getDistributeTemplateSuites } from '@/api/get';
import { storage } from '@/assets/utils/storageUtils';

const showNewTemplateDrawer = ref(false);
const distributionTableData = ref([]);
const templateFormRef = ref(null);
const drawerTitle = ref(null);
const drawerType = ref(null);

const drawerRules = ref({
  templateName: {
    required: true,
    message: '模板名称必填',
    trigger: ['blur', 'input']
  },
  groupName: {
    type: 'number',
    required: true,
    message: '请选择团队',
    trigger: ['blur', 'change']
  },
  templateType: {
    required: true,
    message: '模板类型必填',
    trigger: ['blur', 'input']
  },
  executor: {
    required: true,
    message: '请选择责任人',
    trigger: ['blur', 'change']
  }
});
const drawerModel = ref({
  templateName: null,
  templateType: null,
  groupName: null,
  suiteNames: [],
  executor: null,
  helpers: [],
  suiteSource: 'org'
});

const groupNameOptions = ref([]);
const groupSelectLoading = ref(false);

function getGroupAxios() {
  groupNameOptions.value = [];
  groupSelectLoading.value = true;
  getGroup({
    page_num: 1,
    page_size: 99999999
  })
    .then((res) => {
      groupSelectLoading.value = false;
      if (res.data.items) {
        res.data.items.forEach((item) => {
          groupNameOptions.value.push({
            label: item.name,
            value: item.id
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
      is_admin: true
    })
    .then((res) => {
      userSelectLoading.value = false;
      if (res.data.items) {
        res.data.items.forEach((item) => {
          helpersOptions.value.push({
            label: item.user_name,
            value: item.user_id
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

function handleChangeGroup(value) {
  drawerModel.value.groupName = value;
  drawerModel.value.executor = null;
  drawerModel.value.helpers = [];
  helpersOptions.value = [];
  helpersTemp = [];
  executorOptions.value = [];
  executorTemp = [];
  axios
    .get(`/v1/groups/${value}/users`, {
      page_num: 1,
      page_size: 99999999,
      is_admin: true
    })
    .then((res) => {
      if (res.data.items) {
        res.data.items.forEach((item) => {
          helpersOptions.value.push({
            label: item.user_name,
            value: item.user_id
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
  helpersOptions.value = helpersTemp.filter((item) => ~item.label.indexOf(query));
}

function handleExecutorSearch(query) {
  if (!query.length) {
    executorOptions.value = executorTemp;
    return;
  }
  executorOptions.value = executorTemp.filter((item) => ~item.label.indexOf(query));
}

function handleChangeExecutor(v) {
  helpersOptions.value = [];
  helpersTemp = [];
  axios
    .get(`/v1/groups/${drawerModel.value.groupName}/users`, {
      except_list: v,
      page_num: 1,
      page_size: 99999999,
      is_admin: true
    })
    .then((res) => {
      if (res.data.items) {
        res.data.items.forEach((item) => {
          helpersOptions.value.push({
            label: item.user_name,
            value: item.user_id
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
      is_admin: true
    })
    .then((res) => {
      if (res.data.items) {
        res.data.items.forEach((item) => {
          executorOptions.value.push({
            label: item.user_name,
            value: item.user_id
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
  return drawerType.value === 'newTemplateType' || drawerType.value === 'editTemplateType';
}

const distributionLoading = ref(false);
const templatePagination = reactive({
  page: 1,
  pageCount: 1, //总页数
  pageSize: 10, //受控模式下的分页大小
  showSizePicker: true,
  pageSizes: [5, 10, 20, 50]
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
      group: item.group.name
    });
    if (item.types) {
      distributionTableData.value[i].children = [];
      item.types.forEach((type, j) => {
        let helpers = type.helpers?.map((helper) => helper.user_name).join(',');
        distributionTableData.value[i].children.push({
          key: index++,
          level: 'templateType',
          templateNameID: item.id,
          templateName: item.name,
          templateTypeID: type.id,
          templateType: type.name,
          groupID: item.group.id,
          group: item.group.name,
          creator: type.creator.user_name,
          executor: type.executor.user_name,
          helper: helpers,
          creatingTime: formatTime(type.create_time, 'yyyy-MM-dd hh:mm:ss'),
          suite_source: type.suite_source
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
              creator: type.creator.user_name,
              executor: type.executor.user_name,
              helper: helpers,
              creatingTime: formatTime(type.create_time, 'yyyy-MM-dd hh:mm:ss')
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
  getDistributeTemplates({
    page_num: templatePagination.page,
    page_size: templatePagination.pageSize
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
function handleTemplatePageSizeChange(pageSize) {
  if (!distributionLoading.value) {
    templatePagination.page = 1;
    templatePagination.pageSize = pageSize;
    getTemplateTableData();
  }
}

function deleteTemplateName(templateNameID) {
  axios
    .delete(`/v1/tasks/distribute-templates/${templateNameID}`)
    .then(() => {
      getTemplateTableData();
    })
    .catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

function deleteTemplateType(templateTypeID) {
  axios
    .delete(`/v1/tasks/distribute-templates/types/${templateTypeID}`)
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
            if (cancelCb) {
              cancelCb();
            }
          }
        },
        '取消'
      );
      return [cancelmBtn, confirmBtn];
    }
  });
}

// 获取模板类型数据
function getTemplateType(value) {
  drawerModel.value.suiteNames = [];
  drawerModel.value.executor = null;
  drawerModel.value.helpers = [];
  let params = {
    page_num: 1,
    page_size: 99999999,
    type_id: value,
  };
  getDistributeTemplateSuites(params)
    .then((res) => {
      drawerModel.value.executor = res.data.executor.user_id;
      if (res.data.helpers) {
        res.data.helpers.forEach((item) => {
          drawerModel.value.helpers.push(item.user_id);
        });
      }
      handleChangeExecutor(drawerModel.value.executor);
      handleChangeHelper(drawerModel.value.helpers);
      getGroupAxios();
    })
    .catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

const suiteLoading = ref(false);
const suiteOptions = ref([]);

const suiteOptionsLoad = (option) => {
  suiteLoading.value = true;
  option.children = [];
  return new Promise((resolve, reject) => {
    getCaseNode(option.info?.id)
      .then((res) => {
        suiteLoading.value = false;
        for (const item of res.data.children) {
          let newKey = `${item.type}-${item.id}`;
          if (item.type === 'suite') {
            newKey = item.suite_id;
          }
          option.children.push({
            label: item.title,
            info: item,
            key: newKey,
            isLeaf: item.type === 'suite',
            type: item.type,
            parent: option,
            suiteId: item.suite_id,
            caseId: item.case_id
          });
        }
        resolve(option.children);
      })
      .catch((err) => {
        suiteLoading.value = false;
        reject(err);
      });
  });
};

const setNodeOptions = (array) => {
  return array.map((item) => {
    let newKey = `${item.type}-${item.id}`;
    if (item.type === 'suite') {
      newKey = item.suite_id;
    }

    return {
      label: item.title,
      info: item,
      key: newKey,
      isLeaf: item.type === 'suite',
      type: item.type
    };
  });
};

const getCaseSetNodesAxios = (type, id) => {
  suiteLoading.value = true;
  getCaseSetNodes(type, id).then((res) => {
    suiteOptions.value = [];
    suiteLoading.value = false;
    if (type === 'org') {
      for (const i in res.data) {
        suiteOptions.value.push({
          label: res.data[i].name,
          key: i,
          disabled: true,
          isLeaf: false,
          children: setNodeOptions(res.data[i].children)
        });
      }
    } else {
      for (const i in res.data) {
        if (i === 'group') {
          suiteOptions.value.push({
            label: res.data[i].name,
            key: i,
            disabled: true,
            isLeaf: false,
            children: setNodeOptions(res.data[i].children)
          });
        }
      }
    }
  });
};

const changeSuiteSource = (value) => {
  if (value === 'org') {
    getCaseSetNodesAxios('org', storage.getValue('loginOrgId'));
  } else {
    getCaseSetNodesAxios('group', drawerModel.value.groupName);
  }
};

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
        getCaseSetNodesAxios('org', storage.getValue('loginOrgId'));
      }
    },
    {
      default: () => '新增'
    }
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
          drawerModel.value.suiteSource = rowData.suite_source;
          drawerType.value = 'editTemplateType';
          if (drawerModel.value.suiteSource === 'org') {
            getCaseSetNodesAxios('org', storage.getValue('loginOrgId'));
          } else {
            getCaseSetNodesAxios('group', drawerModel.value.groupName);
          }
          drawerShowCb(drawerType.value);
          getTemplateType(rowData.templateTypeID);
        }
      }
    },
    {
      default: () => '修改'
    }
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
          warning('删除模板', '您确定要删除此模板吗？', () => deleteTemplateName(rowData.templateNameID));
        } else if (rowData.level === 'templateType') {
          warning('删除模板类型', '您确定要删除此模板类型吗？', () => deleteTemplateType(rowData.templateTypeID));
        }
      }
    },
    {
      default: () => '删除'
    }
  );
}
// 复制菜单
function operateMenuCopy() {
  return h(
    NButton,
    {
      type: 'primary',
      text: true,
      style: 'margin-left:10px;',
      onClick: () => {
        warning('复制模板', '您确定要复制此模板吗？', () => {
          window.$message?.warning('暂未接入接口');
        });
      }
    },
    {
      default: () => '复制'
    }
  );
}

const distributionColumns = [
  {
    title: '模板名称',
    key: 'templateName',
    align: 'left'
  },
  {
    title: '团队',
    key: 'group',
    align: 'center'
  },
  {
    title: '模板类型',
    key: 'templateType',
    align: 'center'
  },
  {
    title: '测试套',
    key: 'suiteName',
    align: 'center'
  },
  {
    title: '创建人',
    key: 'creator',
    align: 'center'
  },
  {
    title: '责任人',
    key: 'executor',
    align: 'center'
  },
  {
    title: '协助人',
    key: 'helper',
    align: 'center'
  },
  {
    title: '创建日期',
    key: 'creatingTime',
    align: 'center'
  },
  {
    title: '操作',
    key: 'operate',
    align: 'center',
    render(rowData) {
      if (rowData.level === 'templateName') {
        return [operateMenuAdd(rowData), operateMenuEdit(rowData), operateMenuDelete(rowData), operateMenuCopy(rowData)];
      } else if (rowData.level !== 'suiteName') {
        return [operateMenuEdit(rowData), operateMenuDelete(rowData)];
      }
      return null;
    }
  }
];

// 点击“创建模板”按钮
function showAddTemplateBtn() {
  drawerType.value = 'newTemplate';
  drawerShowCb(drawerType.value);
  getGroupAxios();
}

// 取消
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
        .post('/v1/tasks/distribute-templates', {
          name: drawerModel.value.templateName,
          group_id: drawerModel.value.groupName
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
        .post(`/v1/tasks/distribute-templates/${drawerModel.value.templateNameID}/types`, {
          name: drawerModel.value.templateType,
          executor_id: drawerModel.value.executor,
          suites: drawerModel.value.suiteNames,
          helpers: drawerModel.value.helpers,
          suite_source: drawerModel.value.suiteSource
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

// 修改模板名称回调
function editTemplateNameCb() {
  templateFormRef.value.validate((error) => {
    if (error) {
      window.$message?.error('请填写相关信息');
    } else {
      axios
        .put(`/v1/tasks/distribute-templates/${drawerModel.value.templateNameID}`, {
          name: drawerModel.value.templateName
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

// 修改模板类型数据回调
function editTemplateTypeCb() {
  templateFormRef.value.validate((error) => {
    if (error) {
      window.$message?.error('请填写相关信息');
    } else {
      axios
        .put(`/v1/tasks/distribute-templates/types/${drawerModel.value.templateTypeID}`, {
          name: drawerModel.value.templateType,
          executor_id: drawerModel.value.executor,
          suites: drawerModel.value.suiteNames,
          helpers: drawerModel.value.helpers,
          suite_source: drawerModel.value.suiteSource
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
  handleTemplatePageSizeChange,
  drawerTypeJudge,
  groupSelectLoading,
  userSelectLoading,
  suiteOptions,
  suiteOptionsLoad,
  suiteLoading,
  changeSuiteSource
};
