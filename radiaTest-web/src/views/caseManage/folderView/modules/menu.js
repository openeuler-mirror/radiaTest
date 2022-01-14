import { h, ref } from 'vue';

import axios from '@/axios.js';
import { storage } from '@/assets/utils/storageUtils';
import { Organization20Regular, Folder16Regular, Delete28Regular, Box16Regular } from '@vicons/fluent';
import { GroupsFilled, DriveFileRenameOutlineFilled, CreateNewFolderOutlined } from '@vicons/material';
import { MdRefresh } from '@vicons/ionicons4';
import { FileImport, DatabaseImport, File } from '@vicons/tabler';
import { Database } from '@vicons/fa';
import { ExportOutlined } from '@vicons/antd';
import { ArchiveOutline } from '@vicons/ionicons5';
import { NButton, NFormItem, NInput, NSpace, NIcon, NSelect, NUpload, NUploadDragger, NText, NP } from 'naive-ui';
import router from '@/router';
import { createModalRef,createFormRef } from './createRef';

function renderIcon (icon) {
  return () => h(NIcon, null, {
    default: () => h(icon)
  });
}
const iconType = {
  'org': Organization20Regular,
  'group': GroupsFilled,
  'directory': Folder16Regular,
  'suite': Box16Regular,
  'case': File
};
const commonAction = [
  { label: '刷新', key: 'refresh', icon: renderIcon(MdRefresh) },
  { label: '从文件导入', key: 'import', disabled: true, icon: renderIcon(FileImport) },
  { label: '导出到文件', key: 'export', disabled: true, icon: renderIcon(ExportOutlined) }
];
const menuList = ref();
function getOrg () {
  axios.get(`/v1/users/${storage.getValue('gitee_id')}`).then(res => {
    const { data } = res;
    menuList.value = data.orgs.map(item => {
      if (item.re_user_org_default) {
        return {
          label: item.org_name,
          key: `org-${item.org_id}`,
          iconColor: 'rgba(0, 47, 167, 1)',
          isLeaf: false,
          type: 'org',
          icon: Organization20Regular,
        };
      }
      return '';
    });
  });
}
function getGroup (node) {
  return new Promise((resolve, reject) => {
    const actions = [...commonAction];
    actions.unshift({ label: '导入用例集', key: 'importCaseSet', icon: renderIcon(DatabaseImport) });
    actions.unshift({ label: '新建目录', key: 'newDirectory', icon: renderIcon(CreateNewFolderOutlined) });
    axios.get(`/v1/org/${node.key.replace('org-', '')}/groups`, {
      page_num: 1,
      page_size: 99999
    }).then(res => {
      node.children = [];
      for (const item of res.data.items) {
        node.children.push({
          label: item.name,
          key: `users-${item.id}`,
          parent:node,
          isLeaf: false,
          info: {
            group_id: item.id,
          },
          type: 'users',
          iconColor: 'rgba(0, 47, 167, 1)',
          icon: GroupsFilled,
          actions
        });
      }
      resolve(node.children);
    }).catch(err => {
      reject(err);
    });
  });
}
function getDirectory (node) {
  return new Promise((resolve, reject) => {
    const actions = [...commonAction];
    actions.unshift({
      label: '新建', key: 'newParent', icon: renderIcon(CreateNewFolderOutlined), children: [
        {
          label: '子目录',
          key: 'newDirectory'
        },
        {
          label: '测试套',
          key: 'newSuite'
        }
      ]
    });
    actions.push({ label: '删除', key: 'deleteBaseline', icon: renderIcon(Delete28Regular) });
    axios.get('/v1/baseline', {
      group_id: node.key.replace('users-', '')
    }).then(res => {
      node.children = [];
      for (const item of res.data) {
        node.children.push({
          label: item.title,
          key: `directory-${item.id}`,
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
    }).catch(err => {
      reject(err);
    });
  });
}
function getBaseLine (node) {
  return new Promise((resolve, reject) => {
    axios.get(`/v1/baseline/${node.info.id}`).then(res => {
      node.children = [];
      for (const item of res.data.children) {
        const actions = [...commonAction];
        actions.unshift({ label: '重命名', key: 'renameBaseline', disabled: true, icon: renderIcon(DriveFileRenameOutlineFilled) });
        actions.push({ label: '删除', key: 'deleteBaseline', icon: renderIcon(Delete28Regular) });
        if (item.type === 'suite') {
          actions.unshift({ label: '新建测试用例', key: 'newCase', icon: renderIcon(CreateNewFolderOutlined) });
        } else if (item.type === 'directory') {
          actions.unshift({
            label: '新建', key: 'newParent', icon: renderIcon(CreateNewFolderOutlined), children: [
              {
                label: '子目录',
                key: 'newDirectory'
              },
              {
                label: '测试套',
                key: 'newSuite'
              }
            ]
          });
        }
        node.children.push({
          label: item.title,
          info: item,
          key: `${item.type}-${item.id}`,
          isLeaf: item.type === 'case',
          type: item.type,
          iconColor: 'rgba(0, 47, 167, 1)',
          icon: iconType[item.type],
          actions,
          parent: node
        });
      }
      resolve(node.children);
    }).catch(err => {
      reject(err);
    });
  });
}
function loadData (node, callback) {
  switch (node.type) {
    case 'org':
      getGroup(node).then(() => {
        callback('success');
      }).catch(err => {
        callback(err);
      });
      break;
    case 'users':
      getDirectory(node).then(() => {
        callback('success');
      }).catch(err => {
        callback(err);
      });
      break;
    default:
      getBaseLine(node).then(() => {
        callback('success');
      }).catch(err => {
        callback(err);
      });
      break;
  }
}
const info = ref('');
const inputInfo = ref('');
const infoRules = {
  trigger: ['input', 'blur', 'change'],
  validator () {
    if (info.value === '') {
      return new Error('请填写信息');
    }
    return '';
  }
};
const inputInfoRules = {
  trigger: ['input', 'blur'],
  validator () {
    if (inputInfo.value === '') {
      return new Error('必填项');
    }
    return '';
  }
};
function dialogAction (confirmFn, node, d, contentType) {
  const confirmBtn = h(NButton, {
    size: 'large',
    type: 'primary',
    ghost: true,
    onClick: () => {
      if (contentType === 'directory') {
        if (infoRules.validator() === '') {
          confirmFn(node);
          d.destroy();
        }
      } else if (inputInfoRules.validator() === '' && infoRules.validator() === '') {
        confirmFn(node);
        d.destroy();
      } else {
        window.$message?.error('信息有误，请检查!');
      }
    }
  }, '确定');
  const cancelBtn = h(NButton, {
    size: 'large',
    type: 'error',
    ghost: true,
    onClick: () => d.destroy(),
  }, '取消');
  return h(NSpace, {
    style: 'width:100%',
  }, [cancelBtn, confirmBtn]);
}

function newDectoryContent () {
  const form = h('div', null, [
    h(NFormItem, {
      label: '目录名称:',
      rule: infoRules
    }, h(NInput, {
      value: info.value,
      onUpdateValue: value => {
        info.value = value;
      }
    }))
  ]);
  return form;
}
const suiteList = ref([]);
function getSuite () {
  axios.get('/v1/suite').then(res => {
    suiteList.value = res.map(item => {
      return {
        label: item.name,
        value: item.id
      };
    });
  });
}
function newFormContent (titleTip, selectTip, list) {
  if (suiteList.value.length === 0) {
    getSuite();
  }
  const form = h('div', null, [
    h(NFormItem, {
      label: titleTip,
      rule: inputInfoRules
    }, h(NInput, {
      value: inputInfo.value,
      onUpdateValue: value => {
        inputInfo.value = value;
      }
    })),
    h(NFormItem, {
      label: selectTip,
      rule: infoRules
    }, h(NSelect, {
      value: info.value,
      options: list,
      onUpdateValue: value => {
        info.value = value;
      }
    }))
  ]);
  return form;
}
const caseList = ref();
function getCase (id) {
  axios.get('/v1/case', {
    suite_id: id
  }).then(res => {
    if (Array.isArray(res)) {
      caseList.value = res.map(item => {
        return {
          label: item.name,
          value: item.id
        };
      });
    }
  }).catch(err => {
    window.$message?.error(err.data.error_msg || '未知错误');
  });
}
function uploadContent (node) {
  const description = h(NP, {
    depth: 3,
    style: 'margin:8px 0 0 0'
  }, '仅支持zip,rar,tar,gz,xz,bz2压缩文件上传');
  const tip = h(NText, null, '点击或者拖动文件到该区域来上传');
  const icon = h('div', {
    style: 'margin-bottom: 12px;'
  }, h(NIcon, {
    size: 48,
    depth: 3
  }, h(ArchiveOutline)));
  return h(NUpload, {
    data: {
      group_id: node.info.group_id
    },
    action: '/api/v1/baseline/case_set',
    accept: '.rar,.zip,.tar,.gz,.xz,.bz2',
    withCredentials: true,
    showRemoveButton: false,
    headers: {
      authorization: `JWT ${storage.getValue('token')}`
    },
    onFinish: () => {
      getDirectory(node);
    },
    onBeforeUpload: ({ file }) => {
      const suffix = file.name.split('.').pop();
      const vaildSuffix = ['rar', 'zip', 'gz', 'xz', 'bz2'];
      if (!vaildSuffix.includes(suffix)) {
        window.$message?.error('上传文件格式不对!');
        return false;
      }
      return true;
    }
  }, h(NUploadDragger, [icon, tip, description]));
}
function dialogView (confirmFn, node, contentType = 'directory') {
  const d = window.$dialog?.info({
    title: node.label,
    showIcon: false,
    content: () => {
      switch (contentType) {
        case 'directory':
          return newDectoryContent();
        case 'suite':
          return newFormContent('名称:', '测试套:', suiteList.value);
        case 'case':
          getCase(node.info.suite_id);
          return newFormContent('名称:', '测试用例:', caseList.value);
        case 'caseSet':
          return uploadContent(node);
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
function newDirectory (node) {
  axios.post('/v1/baseline', {
    title: info.value,
    type: 'directory',
    group_id: node.info.group_id,
    parent_id: node.info.id
  }).then(() => {
    window.$message.success('创建成功');
    if (node.type === 'directory') {
      getBaseLine(node);
    } else {
      getDirectory(node);
    }
  }).catch(err => {
    window.$message.error(err.data.error_msg || '未知错误');
  });
}
function newSuite (node) {
  axios.post('/v1/baseline', {
    title: node.label,
    type: 'suite',
    group_id: node.info.group_id,
    parent_id: node.info.id,
    suite_id: info.value
  }).then(() => {
    window.$message.success('创建成功');
    getBaseLine(node);
  }).catch(err => {
    window.$message.error(err.data.error_msg || '未知错误');
  });
}
function deleteBaseLine (node) {
  axios.delete(`/v1/baseline/${node.info.id}`).then(() => {
    const index = node.parent.children.findIndex(item => item.info.id === node.info.id);
    node.parent.children.splice(index, 1);
  }).catch(err => {
    window.$message.error(err.data.error_msg || '未知错误');
  });
}
function renameBaseLine (node) {
  axios.put(`/v1/baseline/${node.info.id}`, {
    title: info.value
  }).then(() => {
    node.label = info.value;
    info.value = '';
  }).catch(err => {
    window.$message.error(err.data.error_msg || '未知错误');
  });
}
function newCase (node,caseId,title) {
  axios.post('/v1/baseline', {
    type: 'case',
    group_id: node.info.group_id,
    parent_id: node.info.id,
    case_id: caseId ?caseId:info.value,
    title: title ?title:inputInfo.value
  }).then(() => {
    window.$message?.success('添加成功');
  }).catch(err => {
    window.$message?.error(err.data.error_msg || '未知错误');
  });
}
function initDialogViewData () {
  info.value = '';
  inputInfo.value = '';
}
function refreshNode (node) {
  switch (node.type) {
    case 'users':
      getDirectory(node);
      break;
    default:
      getBaseLine(node);
      break;
  }
}
let inSetnode;
function selectAction ({ contextmenu, action }) {
  switch (action.key) {
    case 'newDirectory':
      initDialogViewData();
      dialogView(newDirectory, contextmenu);
      break;
    case 'newSuite':
      if (contextmenu.info.in_set) {
        window.$message?.info('该功能开发中....');
      } else {
        initDialogViewData();
        dialogView(newSuite, contextmenu, 'suite');
      }
      break;
    case 'deleteBaseline':
      deleteBaseLine(contextmenu);
      break;
    case 'renameBaseline':
      renameBaseLine(contextmenu);
      break;
    case 'newCase':
      if (contextmenu.info.in_set) {
        createModalRef.value.show();
        inSetnode = contextmenu;
      } else {
        initDialogViewData();
        dialogView(newCase, contextmenu, 'case');
      }
      break;
    case 'importCaseSet':
      dialogView(null, contextmenu, 'caseSet');
      break;
    case 'refresh':
      refreshNode(contextmenu);
      break;
    default:
      break;
  }
}
const selectKey = ref();
function menuClick (options) {
  selectKey.value = options;
  const [key, id] = options[0].split('-');
  if (key !== 'case') {
    router.push({
      path: '/home/tcm/folderview/taskDetail/development'
    });
  } else {
    router.push({
      path: `/home/tcm/folderview/taskDetail/${id}`
    });
  }
}
const expandKeys = ref([]);
function findeItem (array, key, value) {
  return array.find(item => Number(item.info[key]) === Number(value));
}

function getNode (baselineId) {
  axios.get(`/v1/baseline/${baselineId}`).then(res => {
    const treePath = [];
    treePath.push(res.data.group_id);
    if (Array.isArray(res.data.source) && res.data.source.length) {
      treePath.push(...res.data.source.reverse());
    }
    let index = 0;
    selectKey.value = `case-${treePath[treePath.length - 1]}`;
    treePath.reduce((pre, current, currentIndex) => {
      return new Promise((resolve) => {
        if (currentIndex === 1) {
          getGroup(menuList.value[0]).then(node => {
            expandKeys.value = [menuList.value[0].key];
            const group = findeItem(node, 'group_id', treePath[index]);
            getDirectory(group).then(directory => {
              expandKeys.value.push(group.key);
              index++;
              const baseline = findeItem(directory, 'id', treePath[index]);
              resolve(baseline);
            });
          });
        } else {
          pre.then(node => {
            getBaseLine(node).then(baselines => {
              index++;
              const baseline = findeItem(baselines, 'id', treePath[index]);
              expandKeys.value.push(node.key);
              resolve(baseline);
            });
          });
        }
      });
    });
  });
}
function submitCreateCase () {
  createFormRef.value.post().then(res => {
    if (res.result.data.id) {
      newCase(inSetnode, res.result.data.id, res.form.name);
    }
  });
}
function expandNode (baselineId) {
  let timer = null;
  timer = setInterval(() => {
    if (menuList.value[0].key) {
      clearInterval(timer);
      getNode(baselineId);
    }
  }, 500);
}
function expand (option) {
  expandKeys.value = option;
}
function clearSelectKey () {
  selectKey.value = '';
}

export {
  selectKey,
  menuList,
  expandKeys,
  loadData,
  selectAction,
  menuClick,
  getOrg,
  expand,
  expandNode,
  newCase,
  submitCreateCase,
  clearSelectKey,
};
