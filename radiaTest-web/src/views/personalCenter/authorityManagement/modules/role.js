import { ref } from 'vue';
import axios from '@/axios';
import { renderIcon } from '@/assets/utils/icon';
import { User } from '@vicons/tabler';
import { Organization20Regular } from '@vicons/fluent';
import { GroupsFilled } from '@vicons/material';
import router from '@/router';
import { storage } from '@/assets/utils/storageUtils';

const roleList = ref([]);
const activeRole = ref({});
const expandRole = ref([]);
function setActiveRole (value) {
  activeRole.value = value;
}
function renderGroup (options) {
  const index = roleList.value.findIndex((item) => item.key === 'group');
  const group = roleList.value[index].children.find(
    (item) =>
      window
        .atob(item.key)
        .split('-')
        .pop() === String(options.group_id)
  );
  if (group) {
    group.children.push({
      key: window.btoa(options.id),
      info: options,
      prefix: renderIcon(User),
      label: options.name,
    });
  } else {
    roleList.value[index].children.push({
      key: window.btoa(`group-${options.group_id}`),
      label: options.group_name,
      prefix: renderIcon(GroupsFilled),
      children: [
        {
          label: options.name,
          info: options,
          key: window.btoa(options.id),
          prefix: renderIcon(User),
        },
      ],
    });
  }
}
function renderOrg (options) {
  const index = roleList.value.findIndex((item) => item.key === 'org');
  const org = roleList.value[index].children.find(
    (item) =>
      window
        .atob(item.key)
        .split('-')
        .pop() === String(options.org_id)
  );
  if (org) {
    org.children.push({
      key: window.btoa(options.id),
      info: options,
      prefix: renderIcon(User),
      label: options.name,
    });
  } else {
    roleList.value[index].children.push({
      key: window.btoa(`org-${options.org_id}`),
      label: options.org_name,
      prefix: renderIcon(Organization20Regular),
      children: [
        {
          label: options.name,
          info: options,
          key: window.btoa(options.id),
          prefix: renderIcon(User),
        },
      ],
    });
  }
}
function renderUser (options) {
  const index = roleList.value.findIndex((item) => item.key === 'person');
  if (index !== -1) {
    roleList.value[index].children.push({
      label: options.name,
      info: options,
      key: window.btoa(`person-${options.id}`),
      prefix: renderIcon(User),
    });
  }
}
function initRoleList () {
  if (storage.getValue('role') === 1) {
    roleList.value = [
      {
        label: '平台',
        key: 'public',
      },
      {
        label: '组织',
        key: 'org',
        children: [],
      },
      {
        label: '团队',
        key: 'group',
        children: [],
      },
      {
        label: '个人',
        key: 'person',
        children: []
      }
    ];
  } else {
    roleList.value = [
      {
        label: '平台',
        key: 'public',
        children: [],
      },
      {
        label: '组织',
        key: 'org',
        children: [],
      },
      {
        label: '团队',
        key: 'group',
        children: [],
      },
    ];
  }
  roleList.value.forEach((item) => {
    item.children = [];
  });
}
function renderOptionByKey (key, isActive, item, renderFn) {
  if (isActive) {
    expandRole.value = [key, window.btoa(`${key}-${item[`${key}_id`]}`)];
    activeRole.value.scopeType = item.type;
    activeRole.value.ownerId = item[`${key}_id`];
  }
  renderFn(item);
}
function renderRole () {
  axios.get('/v1/role').then((res) => {
    initRoleList();
    res.data?.forEach((item) => {
      let isActive = false;
      if (String(item.id) === window.atob(activeRole.value.roleId)) {
        isActive = true;
      }
      const renderFn = {
        org: renderOrg,
        group: renderGroup,
      };
      const pubIndex = roleList.value.findIndex((i) => i.key === 'public');
      if (item.type === 'public') {
        if (isActive) {
          expandRole.value = ['public', window.btoa(item.id)];
          activeRole.value.scopeType = 'public';
        }
        pubIndex !== -1 &&
          roleList.value[pubIndex].children.push({
            info: item,
            prefix: renderIcon(User),
            label: item.name,
            key: window.btoa(item.id),
          });
      } else if (item.type === 'person') {
        if (isActive) {
          expandRole.value = ['person', window.btoa(`person-${item.id}`)];
        }
        renderUser(item);
      } else {
        renderOptionByKey(item.type, isActive, item, renderFn[item.type]);
      }
    });
  });
}
function getRoleList () {
  if (router.currentRoute.value.name === 'rolesManagement') {
    activeRole.value.roleId = router.currentRoute.value.params.roleId;
  } else {
    activeRole.value.roleId = '';
  }
  renderRole();
}

function selectRole (key, options) {
  if (options[0].children) {
    return;
  }
  let _ownerId = null;
  if (options[0].info.type === 'org') {
    _ownerId = options[0].info.org_id;
  } else if (options[0].info.type === 'group') {
    _ownerId = options[0].info.group_id;
  }
  activeRole.value = {
    roleId: key[0],
    scopeType: options[0].info.type,
    ownerId: _ownerId,
  };
  router.push({
    name: 'rolesManagement',
    params: { roleId: activeRole.value.roleId },
  });
}

function expandKey (keys) {
  expandRole.value = keys;
}
const roleCreateForm = ref();
function createRole () {
  roleCreateForm.value.show();
}
function submitCreateFrom ({ data, type }) {
  if (type === 'create') {
    axios
      .post('/v1/role', data)
      .then(() => {
        window.$message?.success('创建成功!');
        getRoleList();
      })
      .catch((err) => window.$message?.error(err.data.error_msg || '未知错误'));
  } else {
    axios
      .put('/v1/role', data)
      .then(() => {
        window.$message?.success('修改成功!');
        getRoleList();
      })
      .catch((err) => window.$message?.error(err.data.error_msg || '未知错误'));
  }
}
export {
  roleCreateForm,
  roleList,
  activeRole,
  expandRole,
  getRoleList,
  setActiveRole,
  selectRole,
  expandKey,
  createRole,
  submitCreateFrom,
};
