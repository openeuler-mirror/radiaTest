import { h, ref } from 'vue';

import axios from '@/axios.js';
import { storage } from '@/assets/utils/storageUtils';
import { Organization20Regular, Folder16Regular, Delete28Regular, Box16Regular } from '@vicons/fluent';
import {
  GroupsFilled,
  DriveFileRenameOutlineFilled,
  CreateNewFolderOutlined,
  DriveFileMoveRound
} from '@vicons/material';
import { MdRefresh } from '@vicons/ionicons4';
import { FileImport, DatabaseImport, File } from '@vicons/tabler';
import { Database } from '@vicons/fa';
import { ExportOutlined, EditOutlined } from '@vicons/antd';
import { ArchiveOutline } from '@vicons/ionicons5';
import { ChartRelationship, Milestone } from '@vicons/carbon';
import { changeLoadingStatus } from '@/assets/utils/loading';
import { putModalRef, updateModalRef } from './editRef';
import { getDetail } from '@/views/caseManage/folderView/testcaseNodes/modules/details';
import store from '@/store';
import {
  getCaseDetail,
  getCaseSetNodes,
  getGroupMilestone,
  getOrgMilestone,
  getBaselineTemplates,
  getCaseNodeRoot,
  getOrphanOrgSuites,
  getOrphanGroupSuites,
  getCasesBySuite
} from '@/api/get';
import { addBaseline, casenodeApplyTemplate } from '@/api/post';
import { updateCaseNodeParent } from '@/api/put';
import {
  NButton,
  NFormItem,
  NInput,
  NSpace,
  NIcon,
  NSelect,
  NUpload,
  NUploadDragger,
  NText,
  NP,
  NTreeSelect
} from 'naive-ui';
import router from '@/router';
import { createModalRef, createFormRef, importModalRef } from './createRef';
import { workspace } from '@/assets/config/menu.js';

function renderIcon(icon) {
  return () =>
    h(NIcon, null, {
      default: () => h(icon)
    });
}
const suiteInfo = ref();

const createSuitesShow = ref(false);
const orphanSuitesData = ref([]);
const createSuitesTargetNode = ref({});
const orphanSuitesPagination = reactive({
  page: 1,
  pageCount: 1,
  itemCount: 1,
  pageSize: 10,
  showSizePicker: true,
  pageSizes: [5, 10, 20, 50]
});

const renameAction = {
  label: '重命名',
  key: 'renameCaseNode',
  icon: renderIcon(DriveFileRenameOutlineFilled)
};
const editAction = {
  label: '修改',
  key: 'editCaseNode',
  icon: renderIcon(EditOutlined)
};
const deleteAction = {
  label: '删除',
  key: 'deleteCaseNode',
  icon: renderIcon(Delete28Regular)
};
const createChildrenDirectoryAction = {
  label: '新建子目录',
  key: 'newDirectory',
  icon: renderIcon(Folder16Regular)
};
const createChildrenAction = {
  label: '新建',
  key: 'newParent',
  icon: renderIcon(CreateNewFolderOutlined),
  children: [
    {
      label: '子目录',
      key: 'newDirectory',
      icon: renderIcon(Folder16Regular)
    },
    {
      label: '测试套',
      key: 'relateSuite',
      icon: renderIcon(Box16Regular)
    }
  ]
};
const relateSuiteAction = {
  label: '关联测试套',
  key: 'relateSuite',
  icon: renderIcon(Box16Regular)
};
const exportTestcaseAction = {
  label: '导出文本用例',
  key: 'exportTestcase',
  disabled: true,
  icon: renderIcon(ExportOutlined)
};
const importTestcaseAction = {
  label: '导入用例',
  key: 'importCase',
  icon: renderIcon(FileImport)
};
const exportCasesetAction = {
  label: '导出用例集',
  key: 'exportSet',
  disabled: true,
  icon: renderIcon(ExportOutlined)
};
const relateTestcaseAction = {
  label: '关联测试用例',
  key: 'relateCase',
  icon: renderIcon(ChartRelationship)
};
const createTestcaseAction = {
  label: '新建测试用例',
  key: 'newCase',
  icon: renderIcon(CreateNewFolderOutlined)
};
const createBaselineAction = {
  label: '新建版本基线',
  key: 'newBaseline',
  icon: renderIcon(Milestone)
};
const applyBaselineTemplate = {
  label: '应用基线模板',
  key: 'applyTemplate',
  icon: renderIcon(FileImport)
};
const moveCaseNodeAction = {
  label: '移动到...',
  key: 'moveCaseNode',
  icon: renderIcon(DriveFileMoveRound)
};

const iconType = {
  org: Organization20Regular,
  group: GroupsFilled,
  baseline: Milestone,
  directory: Folder16Regular,
  suite: Box16Regular,
  case: File
};
const commonAction = [{ label: '刷新', key: 'refresh', icon: renderIcon(MdRefresh) }];

const frameworkList = ref([]);

const menuList = ref();
const expandKeys = ref([]);

function getDirectory(node) {
  const params = {};
  if (node && node.type === 'org') {
    params.org_id = node.key.replace('org-', '');
  } else if (node && node.type === 'group') {
    params.group_id = node.key.replace('group-', '');
  } else {
    return new Promise(() => {});
  }
  return new Promise((resolve, reject) => {
    axios
      .get(`/v1/ws/${workspace.value}/case-node`, params)
      .then((res) => {
        node.children = [];
        for (const item of res.data) {
          const actions = [...commonAction];
          actions.push(deleteAction);
          if (item.in_set) {
            actions.unshift(importTestcaseAction);
            actions.unshift(exportCasesetAction);
            actions.unshift(createChildrenAction);
          } else {
            actions.unshift(renameAction);
            actions.unshift(relateSuiteAction);
            actions.unshift(createChildrenDirectoryAction);
            actions.unshift(applyBaselineTemplate);
          }

          node.children.push({
            label: item.title,
            key: `${item.type}-${item.id}`,
            isLeaf: false,
            type: item.type,
            info: item,
            iconColor: 'rgba(0, 47, 167, 1)',
            icon: item.title === '用例集' ? Database : iconType[item.type],
            parent: node,
            actions
          });
        }
        resolve(node.children);
      })
      .catch((err) => {
        reject(err);
      });
  });
}

function createCasesetActions(item) {
  const actions = [...commonAction, deleteAction];
  if (item.type === 'directory') {
    actions.unshift(moveCaseNodeAction);
    actions.unshift(renameAction);
    actions.unshift(importTestcaseAction);
    actions.unshift(createChildrenAction);
  } else if (item.type === 'suite') {
    actions.unshift(moveCaseNodeAction);
    actions.unshift(exportTestcaseAction);
    actions.unshift(createTestcaseAction);
  } else if (item.type === 'case') {
    actions.unshift(editAction);
    actions.unshift(exportTestcaseAction);
  }
  return actions;
}

function createBaselineActions(item) {
  const actions = [moveCaseNodeAction, renameAction, ...commonAction, deleteAction];
  if (item.type === 'directory') {
    actions.unshift(relateSuiteAction);
    actions.unshift(createChildrenDirectoryAction);
  } else if (item.type === 'suite') {
    actions.unshift(exportTestcaseAction);
    actions.unshift(relateTestcaseAction);
  } else if (item.type === 'case') {
    actions.unshift(exportTestcaseAction);
  }
  return actions;
}

function createCaseNodeActions(item) {
  if (item.in_set) {
    return createCasesetActions(item);
  }
  return createBaselineActions(item);
}

function getCaseNode(node, leafType) {
  return new Promise((resolve, reject) => {
    axios
      .get(`/v1/case-node/${node.info?.id}`)
      .then((res) => {
        node.children = [];
        for (const item of res.data.children) {
          const actions = createCaseNodeActions(item);
          let newKey = `${item.type}-${item.id}`;
          if (item.type === 'suite') {
            newKey = `${item.type}-${item.suite_id}`;
          } else if (item.type === 'case') {
            newKey = `${item.type}-${item.case_id}`;
          }
          node.children.push({
            label: item.title,
            info: item,
            key: `${item.type}-${item.id}`,
            relationKey: newKey,
            isLeaf: item.type === 'case' || item.type === leafType,
            type: item.type,
            iconColor: 'rgba(0, 47, 167, 1)',
            icon: iconType[item.type],
            actions,
            parent: node,
            suiteId: item.suite_id,
            caseId: item.case_id
          });
        }
        resolve(node.children);
      })
      .catch((err) => {
        reject(err);
      });
  });
}

function loadData(node, callback) {
  if (!node.root) {
    getCaseNode(node)
      .then(() => {
        callback('success');
      })
      .catch((err) => {
        callback(err);
      });
  } else {
    getDirectory(node)
      .then(() => {
        callback('success');
      })
      .catch((err) => {
        callback(err);
      });
  }
}

function getRootNodes() {
  const actions = [...commonAction];
  actions.unshift({
    label: '导入用例集',
    key: 'importCaseSet',
    icon: renderIcon(DatabaseImport)
  });
  actions.unshift(createBaselineAction);
  menuList.value = [];
  axios.get(`/v1/users/${storage.getValue('user_id')}`).then((res) => {
    const { data } = res;
    data.orgs.forEach((item) => {
      if (item.re_user_org_default) {
        menuList.value.push({
          label: item.org_name,
          key: `org-${item.org_id}`,
          info: {
            org_id: item.org_id
          },
          actions,
          iconColor: 'rgba(0, 47, 167, 1)',
          isLeaf: false,
          type: 'org',
          root: true,
          icon: Organization20Regular
        });
      }
    });
    axios
      .get(`/v1/org/${storage.getValue('loginOrgId')}/groups`, {
        page_num: 1,
        page_size: 99999
      })
      .then((_res) => {
        for (const item of _res.data.items) {
          menuList.value.push({
            label: item.name,
            key: `group-${item.id}`,
            isLeaf: false,
            root: true,
            info: {
              group_id: item.id
            },
            type: 'group',
            iconColor: 'rgba(0, 47, 167, 1)',
            icon: GroupsFilled,
            actions
          });
        }
      });
  });
}
const info = ref('');
const inputInfo = ref('');
const infoRules = {
  trigger: ['input', 'blur', 'change'],
  required: true,
  validator() {
    if (info.value === '') {
      return new Error('请填写信息');
    }
    return true;
  }
};

const milestoneId = ref();
const milestoneLoading = ref(false);
const milestoneOptions = ref([]);
const milestoneIdRules = {
  trigger: ['blur', 'change'],
  required: true,
  validator() {
    if (!milestoneId.value) {
      return new Error('版本基线必须关联里程碑');
    }
    return true;
  }
};

const templateId = ref();
const templateLoading = ref(false);
const templateOptions = ref([]);
const templateRules = {
  trigger: ['blur', 'change'],
  required: true,
  validator() {
    if (!templateId.value) {
      return new Error('未选择基线模板');
    }
    return true;
  }
};

const nextParentId = ref();
const moveLoading = ref(false);
const moveOptions = ref([]);
const moveRules = {
  trigger: ['blur', 'change'],
  required: true,
  validator() {
    if (!nextParentId.value) {
      return new Error('未选择移动目的地');
    }
    return true;
  }
};

const files = ref();
function validateUploadInfo() {
  // if (!info.value) {
  //   window.$message?.error('请选择测试框架');
  //   return false;
  // }
  const suffix = files.value[0].name.split('.').pop();
  const vaildSuffix = ['rar', 'zip', 'gz', 'xz', 'bz2', 'tar'];
  if (!vaildSuffix.includes(suffix)) {
    window.$message?.error('上传文件格式不对!');
    return false;
  }
  return true;
}

function handleBaselineDialogConfirm(confirmFn, node, d, contentType) {
  if (contentType === 'baseline') {
    if (milestoneIdRules.validator() === true) {
      confirmFn(node);
      d.destroy();
    }
  } else if (contentType === 'template') {
    if (templateRules.validator() === true) {
      confirmFn(node);
      d.destroy();
    }
  } else {
    window.$message?.error('信息有误，请检查!');
  }
}

function handleNormalDialogConfirm(confirmFn, node, d, contentType) {
  if (contentType === 'directory') {
    if (infoRules.validator() === true) {
      confirmFn(node);
      d.destroy();
    }
  } else if (contentType === 'caseSet') {
    if (validateUploadInfo()) {
      confirmFn(node);
      d.destroy();
    }
  } else if (contentType === 'move') {
    if (moveRules.validator()) {
      confirmFn(node);
      d.destroy();
    }
  } else if (infoRules.validator() === true) {
    confirmFn(node);
    d.destroy();
  } else {
    window.$message?.error('信息有误，请检查!');
  }
}

function dialogAction(confirmFn, node, d, contentType) {
  const confirmBtn = h(
    NButton,
    {
      size: 'large',
      type: 'primary',
      ghost: true,
      onClick: () => {
        if (contentType === 'baseline' || contentType === 'template') {
          handleBaselineDialogConfirm(confirmFn, node, d, contentType);
        } else {
          handleNormalDialogConfirm(confirmFn, node, d, contentType);
        }
      }
    },
    '确定'
  );
  const cancelBtn = h(
    NButton,
    {
      size: 'large',
      type: 'error',
      ghost: true,
      onClick: () => d.destroy()
    },
    '取消'
  );
  return h(
    NSpace,
    {
      style: 'width:100%'
    },
    [cancelBtn, confirmBtn]
  );
}

function newDectoryContent() {
  const form = h('div', null, [
    h(
      NFormItem,
      {
        label: '目录名称:',
        rule: infoRules
      },
      h(NInput, {
        value: info.value,
        onUpdateValue: (value) => {
          info.value = value;
        }
      })
    )
  ]);
  return form;
}

function getCurMilestones(node, query) {
  milestoneLoading.value = true;
  let params = { paged: true };
  if (query) {
    params.name = query;
  }
  if (node.type === 'org') {
    getOrgMilestone(node.info.org_id, params).then((res) => {
      const { data } = res;
      milestoneOptions.value = data.items?.map((item) => {
        return {
          label: item.name,
          value: item.id
        };
      });
      milestoneLoading.value = false;
    });
  } else if (node.type === 'group') {
    getGroupMilestone(node.info.group_id, params).then((res) => {
      const { data } = res;
      milestoneOptions.value = data.items?.map((item) => {
        return {
          label: item.name,
          value: item.id
        };
      });
      milestoneLoading.value = false;
    });
  }
}

function getTemplates(node, query) {
  let params = {};
  if (query) {
    params.title = query;
  }
  if (node.parent.type === 'org') {
    params.org_id = node.info.org_id;
  } else if (node.parent.type === 'group') {
    params.group_id = node.info.group_id;
  }
  getBaselineTemplates(params).then((res) => {
    const { data } = res;
    templateOptions.value = data.map((item) => {
      return {
        label: item.title,
        value: item.id
      };
    });
  });
}

function newBaselineContent(node) {
  const form = h('div', null, [
    h(
      NFormItem,
      {
        label: '基线名称:',
        rule: infoRules
      },
      h(NInput, {
        value: info.value,
        onUpdateValue: (value) => {
          info.value = value;
        }
      })
    ),
    h(
      NFormItem,
      {
        label: '关联里程碑:',
        rule: milestoneIdRules
      },
      h(NSelect, {
        value: milestoneId.value,
        onUpdateValue: (value) => {
          milestoneId.value = value;
        },
        onFocus: () => {
          getCurMilestones(node);
        },
        loading: milestoneLoading.value,
        options: milestoneOptions.value,
        remote: true,
        filterable: true,
        onSearch: (query) => {
          getCurMilestones(node, query);
        }
      })
    )
  ]);
  return form;
}

function applyTemplateContent(node) {
  const form = h('div', null, [
    h(
      NFormItem,
      {
        label: '应用基线模板:',
        rule: templateRules
      },
      h(NSelect, {
        value: templateId.value,
        onUpdateValue: (value) => {
          templateId.value = value;
        },
        onFocus: () => {
          getTemplates(node);
        },
        loading: templateLoading.value,
        options: templateOptions.value,
        remote: true,
        filterable: true,
        onSearch: (query) => {
          getTemplates(node, query);
        }
      })
    )
  ]);
  return form;
}

function moveCaseNodeContent(node) {
  const form = h('div', null, [
    h(
      NFormItem,
      {
        label: '移动到:',
        rule: moveRules
      },
      h(NTreeSelect, {
        value: nextParentId.value,
        onUpdateValue: (value) => {
          nextParentId.value = value;
        },
        renderPrefix: ({ option }) => {
          return h(
            NIcon,
            {
              color: option.iconColor
            },
            {
              default: () => h(option.icon)
            }
          );
        },
        onFocus: () => {
          moveLoading.value = true;
          getCaseNodeRoot(node.info.id).then((res) => {
            moveOptions.value = [];
            moveOptions.value.push({
              label: res.data.title,
              info: res.data,
              key: `${res.data.type}-${res.data.id}`,
              isLeaf: false,
              type: res.data.type,
              iconColor: 'rgba(0, 47, 167, 1)',
              icon: iconType[res.data.type]
            });
            moveLoading.value = false;
          });
        },
        showPath: true,
        loading: moveLoading.value,
        options: moveOptions.value,
        remote: true,
        filterable: true,
        onLoad: (option) => {
          moveLoading.value = true;
          return new Promise((resolve) => {
            getCaseNode(option).then(() => {
              moveLoading.value = false;
              resolve();
            });
          });
        }
      })
    )
  ]);
  return form;
}

// 关联测试套/关联测试用例下拉框选择项
const setNodeOptions = (array, relateType) => {
  return array.map((item) => {
    let newKey = `${item.type}-${item.id}`;
    if (item.type === 'suite') {
      newKey = `suite-${item.suite_id}`;
    } else if (item.type === 'case') {
      newKey = `case-${item.case_id}`;
    }

    return {
      label: item.title,
      info: item,
      key: `${item.type}-${item.id}`,
      relationKey: newKey,
      isLeaf: item.type === relateType,
      type: item.type,
      iconColor: 'rgba(0, 47, 167, 1)',
      icon: iconType[item.type]
    };
  });
};

const caseOptions = ref([]); // 关联测试用例选项

// 关联测试套/关联测试用例弹框
function relateSuiteCaseContent(node, relateType) {
  const titleDict = {
    suite: '测试套',
    case: '测试用例'
  };
  let form;
  if (relateType === 'case') {
    form = h('div', null, [
      h(
        NFormItem,
        {
          label: `关联${titleDict[relateType]}:`,
          rule: infoRules
        },
        h(NTreeSelect, {
          value: info.value,
          multiple: true,
          checkable: true,
          clearable: true,
          filterable: true,
          cascade: true,
          checkStrategy: 'child',
          maxTagCount: 5,
          options: caseOptions.value,
          loading: moveLoading.value,
          onUpdateValue: (value) => {
            info.value = value;
          },
          onFocus: () => {
            moveLoading.value = true;
            caseOptions.value = [{ label: '全选', key: 'allSelected', children: [] }];
            getCasesBySuite({ suite_id: node.info.suite_id }).then((res) => {
              caseOptions.value[0].children = res.data.children.map((item) => {
                return {
                  label: item.title,
                  key: `${item.type}-${item.case_id}`
                };
              });
              moveLoading.value = false;
            });
          }
        })
      )
    ]);
  } else {
    form = h('div', null, [
      h(
        NFormItem,
        {
          label: `关联${titleDict[relateType]}:`,
          rule: infoRules
        },
        h(NTreeSelect, {
          keyField: 'relationKey',
          value: info.value,
          multiple: true,
          checkable: true,
          onUpdateValue: (value) => {
            info.value = value;
          },
          renderPrefix: ({ option }) => {
            return h(
              NIcon,
              {
                color: option.iconColor
              },
              {
                default: () => h(option.icon)
              }
            );
          },
          onFocus: () => {
            let id = '';
            let type = '';
            if (node.info.group_id) {
              id = node.info.group_id;
              type = 'group';
            } else if (node.info.org_id) {
              id = node.info.org_id;
              type = 'org';
            }
            moveLoading.value = true;
            getCaseSetNodes(type, id).then((res) => {
              moveOptions.value = [];
              for (const i in res.data) {
                moveOptions.value.push({
                  label: res.data[i].name,
                  relationKey: i,
                  disabled: true,
                  isLeaf: false,
                  children: setNodeOptions(res.data[i].children, relateType)
                });
              }
              moveLoading.value = false;
            });
          },
          showPath: true,
          cascade: true,
          checkStrategy: 'child',
          loading: moveLoading.value,
          options: moveOptions.value,
          remote: true,
          filterable: true,
          onLoad: (option) => {
            moveLoading.value = true;
            return new Promise((resolve) => {
              getCaseNode(option, relateType).then(() => {
                moveLoading.value = false;
                resolve();
              });
            });
          }
        })
      )
    ]);
  }
  return form;
}

const description = h(
  NP,
  {
    depth: 3,
    style: 'margin:8px 0 0 0'
  },
  '仅支持zip,rar,tar,gz,xz,bz2压缩文件上传'
);

// 导入用例集
function uploadSet(node) {
  const formData = new FormData();
  formData.append('file', files.value[0]?.file);
  formData.append('group_id', node.info.group_id);
  changeLoadingStatus(true);
  axios
    .post('/v1/case-node/case-set', formData)
    .then(() => {
      window.$message?.success('用例集已上传,请到后台任务查看进展');
      getDirectory(node);
      changeLoadingStatus(false);
    })
    .catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
      changeLoadingStatus(false);
    });
}
function renderUpload() {
  const tip = h(NText, null, '点击或者拖动文件到该区域来上传');
  const icon = h(
    'div',
    {
      style: 'margin-bottom: 12px;'
    },
    h(
      NIcon,
      {
        size: 48,
        depth: 3
      },
      h(ArchiveOutline)
    )
  );
  return h(
    NUpload,
    {
      action: '/api/v1/case-node/case-set',
      accept: '.rar,.zip,.tar,.gz,.xz,.bz2',
      withCredentials: true,
      max: 1,
      showRemoveButton: false,
      onUpdateFileList: (file) => {
        files.value = file;
      },
      defaultUpload: false
    },
    h(NUploadDragger, [icon, tip, description])
  );
}

function uploadContent() {
  return h('div', null, [renderUpload()]);
}
function dialogView(confirmFn, node, contentType = 'directory') {
  window.$dialog?.destroyAll();
  const d = window.$dialog?.info({
    title: node.label,
    showIcon: false,
    style: { width: '800px' },
    content: () => {
      switch (contentType) {
        case 'directory':
          return newDectoryContent();
        case 'baseline':
          return newBaselineContent(node);
        case 'template':
          return applyTemplateContent(node);
        case 'move':
          return moveCaseNodeContent(node);
        case 'suite':
          return relateSuiteCaseContent(node, 'suite');
        case 'case':
          return relateSuiteCaseContent(node, 'case');
        case 'caseSet':
          return uploadContent();
        default:
          return newDectoryContent();
      }
    },
    action: () => {
      if (confirmFn) {
        return dialogAction(confirmFn, node, d, contentType);
      }
      return '';
    }
  });
}
function newDirectory(node) {
  axios
    .post('/v1/case-node', {
      title: info.value,
      type: 'directory',
      group_id: node.info.group_id,
      parent_id: node.info.id
    })
    .then(() => {
      window.$message.success('创建成功');
      if (!node.root) {
        getCaseNode(node);
      } else {
        getDirectory(node);
      }
    })
    .catch((err) => {
      window.$message.error(err.data.error_msg || '未知错误');
    });
}
function newBaseline(node) {
  let data = {
    title: info.value,
    milestone_id: milestoneId.value,
    type: 'baseline',
    permission_type: node.type
  };
  if (node.type === 'org') {
    data.org_id = node.info.org_id;
  } else if (node.type === 'group') {
    data.group_id = node.info.group_id;
  }

  addBaseline(data).then(() => {
    window.$message?.info(`已成功创建版本基线：${info.value}`);
    getDirectory(node);
  });
}
function applyTemplate(node) {
  changeLoadingStatus(true);
  casenodeApplyTemplate(node.info.id, templateId.value)
    .then((res) => {
      const length = res.data?.length;
      window.$message?.info(`${node.info.title}已成功增量应用该模板, 新建${length}个节点`);
      getCaseNode(node);
    })
    .finally(() => {
      changeLoadingStatus(false);
    });
}
function moveCaseNode(node) {
  updateCaseNodeParent(node.info.id, nextParentId.value.split('-').at(-1)).then(() => {
    window.$message?.info(`${node.label}已成功移动至目标节点下`);
    getCaseNode(node.parent);
  });
}

// 关联测试套/关联测试用例
function relateSuiteCase(node, nodeType) {
  let data = {
    type: nodeType,
    group_id: node.info.group_id,
    org_id: node.info.org_id,
    parent_id: node.info.id,
    multiselect: true
  };
  let idArray = info.value.map((item) => {
    return Number(item.split('-').at(-1));
  });
  if (nodeType === 'suite') {
    data.suite_ids = idArray;
  } else {
    data.case_ids = idArray;
  }
  axios
    .post('/v1/case-node', data)
    .then(() => {
      window.$message.success('创建中……如未显示请手动刷新目录');
      getCaseNode(node);
    })
    .catch((err) => {
      window.$message.error(err.data.error_msg || '未知错误');
    });
}
function deleteCaseNode(node) {
  changeLoadingStatus(true);
  axios
    .delete(`/v1/case-node/${node.info.id}`)
    .then(() => {
      changeLoadingStatus(false);
      const index = node.parent.children.findIndex((item) => item.info.id === node.info.id);
      node.parent.children.splice(index, 1);
      if (
        router.currentRoute.value.name === 'testcaseNodes' &&
        router.currentRoute.value.params.taskId !== 'development'
      ) {
        getDetail(window.atob(router.currentRoute.value.params.taskId));
      }
    })
    .catch((err) => {
      changeLoadingStatus(false);
      window.$message.error(err.data.error_msg || '未知错误');
    });
}
function renameCaseNode(node) {
  axios
    .put(`/v1/case-node/${node.info.id}`, {
      title: info.value
    })
    .then(() => {
      node.label = info.value;
      info.value = '';
    })
    .catch((err) => {
      window.$message.error(err.data.error_msg || '未知错误');
    });
}
function newCase(node, caseId, title) {
  axios
    .post('/v1/case-node', {
      type: 'case',
      group_id: node.info.group_id,
      parent_id: node.info.id,
      case_id: caseId ? caseId : info.value,
      title: title ? title : inputInfo.value
    })
    .then(() => {
      window.$message?.success('添加成功');
      getCaseNode(node);
    })
    .catch((err) => {
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}

function getOrphanSuitesReq() {
  if (createSuitesTargetNode.value.group_id) {
    getOrphanGroupSuites(createSuitesTargetNode.value.group_id, {
      page_num: orphanSuitesPagination.page,
      page_size: orphanSuitesPagination.pageSize
    }).then((res) => {
      orphanSuitesData.value = res.data.items;
      orphanSuitesPagination.pageCount = res.data.pages;
      orphanSuitesPagination.itemCount = res.data.total;
      createSuitesShow.value = true;
    });
  } else {
    getOrphanOrgSuites({
      page_num: orphanSuitesPagination.page,
      page_size: orphanSuitesPagination.pageSize
    }).then((res) => {
      orphanSuitesData.value = res.data.items;
      orphanSuitesPagination.pageCount = res.data.pages;
      orphanSuitesPagination.itemCount = res.data.total;
      createSuitesShow.value = true;
    });
  }
}

function initDialogViewData() {
  info.value = '';
  inputInfo.value = '';
  milestoneId.value = undefined;
  milestoneOptions.value = [];
  templateId.value = undefined;
  templateOptions.value = [];
  nextParentId.value = undefined;
  moveOptions.value = [];
  moveLoading.value = false;
}
function refreshNode(node) {
  node.root ? getDirectory(node) : getCaseNode(node);
}
let inSetnode;
let importInfo;
const actionHandlder = {
  newDirectory: {
    handler(contextmenu) {
      initDialogViewData();
      dialogView(newDirectory, contextmenu);
    }
  },
  newBaseline: {
    handler(contextmenu) {
      initDialogViewData();
      dialogView(newBaseline, contextmenu, 'baseline');
    }
  },
  applyTemplate: {
    handler(contextmenu) {
      initDialogViewData();
      dialogView(applyTemplate, contextmenu, 'template');
    }
  },
  moveCaseNode: {
    handler(contextmenu) {
      initDialogViewData();
      dialogView(moveCaseNode, contextmenu, 'move');
    }
  },
  relateSuite: {
    handler(contextmenu) {
      if (contextmenu.info.in_set) {
        createSuitesTargetNode.value = contextmenu.info;
        getOrphanSuitesReq();
      } else {
        initDialogViewData();
        dialogView((node) => relateSuiteCase(node, 'suite'), contextmenu, 'suite');
      }
    }
  },
  deleteCaseNode: {
    handler(contextmenu) {
      deleteCaseNode(contextmenu);
    }
  },
  renameCaseNode: {
    handler(contextmenu) {
      initDialogViewData();
      dialogView(renameCaseNode, contextmenu);
    }
  },
  newCase: {
    handler(contextmenu) {
      createModalRef.value.show();
      inSetnode = contextmenu;
    }
  },
  relateCase: {
    handler(contextmenu) {
      initDialogViewData();
      dialogView((node) => relateSuiteCase(node, 'case'), contextmenu, 'case');
    }
  },
  importCaseSet: {
    handler(contextmenu) {
      initDialogViewData();
      dialogView(uploadSet, contextmenu, 'caseSet');
    }
  },
  importCase: {
    handler(contextmenu) {
      importInfo = contextmenu;
      importModalRef.value.show();
    }
  },
  refresh: {
    handler(contextmenu) {
      refreshNode(contextmenu);
    }
  },
  editCaseNode: {
    handler(contextmenu) {
      const [key] = contextmenu.key.split('-');
      if (key === 'suite') {
        const id = contextmenu.info.suite_id;
        axios.get(`/v1/ws/${workspace.value}/suite`, { id }).then((res) => {
          [suiteInfo.value] = res;
          putModalRef.value.show();
        });
      } else if (key === 'case') {
        const id = contextmenu.info.case_id;
        getCaseDetail(id).then((res) => {
          res.data.name = contextmenu.label;
          store.commit('rowData/set', res.data);
          updateModalRef.value.show();
        });
      }
    }
  }
};

// 点击右键菜单
function selectAction({ contextmenu, action }) {
  actionHandlder[action.key].handler(contextmenu);
}
const selectKey = ref();
const selectOptions = ref();
function menuClick({ key, options }) {
  if (!key.length) {
    return;
  }
  selectKey.value = key;
  selectOptions.value = options;
  const [itemkey, id] = key[0].split('-');
  const [{ label, type, suiteId, caseId }] = options;
  if (itemkey === 'org') {
    router.push({
      name: 'orgNode',
      params: {
        taskId: window.btoa(id)
      }
    });
  } else if (itemkey === 'group') {
    router.push({
      name: 'termNode',
      params: {
        taskId: window.btoa(id)
      }
    });
  } else if (itemkey === 'directory' && label === '用例集') {
    router.push({
      name: 'casesetNode',
      params: {
        taskId: window.btoa(id)
      }
    });
  } else if (type === 'baseline') {
    router.push({
      name: 'baselineNode',
      params: {
        taskId: window.btoa(id)
      }
    });
  } else if (itemkey === 'suite') {
    router.push({
      name: 'suiteNode',
      params: {
        taskId: window.btoa(id),
        suiteId: window.btoa(suiteId)
      }
    });
  } else if (itemkey === 'case') {
    router.push({
      name: 'testcaseNodes',
      params: {
        taskId: window.btoa(id),
        caseId: window.btoa(caseId)
      }
    });
  }
}

function findeItem(array, key, value) {
  return array.find((item) => Number(item.info[key]) === Number(value));
}

function getNode(caseNodeId) {
  axios.get(`/v1/case-node/${caseNodeId}`).then((res) => {
    const treePath = [];
    let rootType = null;
    if (res.data.group_id) {
      treePath.push(res.data.group_id);
      rootType = 'group';
    } else {
      treePath.push(res.data.org_id);
      rootType = 'org';
    }
    if (Array.isArray(res.data.source) && res.data.source.length) {
      treePath.push(...res.data.source.reverse());
    }
    let index = 0;
    selectKey.value = `${res.data.type}-${treePath[treePath.length - 1]}`;
    treePath.reduce((pre, current, currentIndex) => {
      return new Promise((resolve) => {
        if (currentIndex === 1) {
          expandKeys.value = [];
          expandKeys.value.push(`${rootType}-${treePath[0]}`);
          const node = menuList.value.find((item) => item.key === `${rootType}-${treePath[0]}`);
          getDirectory(node).then((directory) => {
            expandKeys.value.push(node.key);
            index++;
            const caseNode = findeItem(directory, 'id', treePath[index]);
            resolve(caseNode);
          });
        } else {
          pre.then((node) => {
            getCaseNode(node).then((caseNodes) => {
              index++;
              const caseNode = findeItem(caseNodes, 'id', treePath[index]);
              expandKeys.value.push(node.key);
              resolve(caseNode);
            });
          });
        }
      });
    });
  });
}

function submitCreateCase() {
  createFormRef.value.post().then((res) => {
    if (res.result.data.id) {
      newCase(inSetnode, res.result.data.id, res.form.name);
    }
  });
}
function expandNode(caseNodeId) {
  let timer = null;
  timer = setInterval(() => {
    clearInterval(timer);
    getNode(caseNodeId);
  }, 500);
}
function expandRoot(rootType, id) {
  let timer = null;
  timer = setInterval(() => {
    clearInterval(timer);
    const node = menuList.value.find((item) => item.key === `${rootType}-${id}`);
    selectKey.value = `${rootType}-${id}`;
    expandKeys.value = [];
    expandKeys.value.push(`${rootType}-${id}`);
    getDirectory(node);
  }, 500);
}
function expand(option) {
  expandKeys.value = option;
}
function clearSelectKey() {
  selectKey.value = '';
}
function extendSubmit(value) {
  if (!value.file.length) {
    window.$message?.error('请上传用例文本');
    return;
  }
  const formData = new FormData();
  formData.append('file', value.file[0].file);
  formData.append('case_node_id', importInfo.info.id);
  formData.append('group_id', importInfo.info.group_id);
  formData.append('framework_id', value.data.framework_id);
  axios.post('/v1/case/import', formData).then(() => {
    window.$message?.success('上传成功');
  });
}

export {
  suiteInfo,
  frameworkList,
  selectKey,
  selectOptions,
  menuList,
  expandKeys,
  createSuitesShow,
  orphanSuitesData,
  createSuitesTargetNode,
  orphanSuitesPagination,
  loadData,
  selectAction,
  menuClick,
  getRootNodes,
  expand,
  expandNode,
  expandRoot,
  newCase,
  submitCreateCase,
  clearSelectKey,
  extendSubmit,
  getOrphanSuitesReq
};
