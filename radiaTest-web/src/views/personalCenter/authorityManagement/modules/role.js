import { ref } from 'vue';
import axios from '@/axios';
import { renderIcon } from '@/assets/utils/icon';
import { User } from '@vicons/tabler';
import { Organization20Regular } from '@vicons/fluent';
import { GroupsFilled } from '@vicons/material';
import router from '@/router';

const roleList = ref([
  {
    label: '公共角色',
    key: 'public',
    children: [],
  },
  {
    label: '团队角色',
    key: 'group',
    children: [],
  },
  {
    label: '组织角色',
    key: 'org',
    children: [],
  },
]);
const activeRole = ref('');
const expandRole = ref([]);
function setActiveRole(value) {
  activeRole.value = value;
}
function renderGroup(options) {
  const group = roleList.value[1].children.find(
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
    roleList.value[1].children.push({
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
// function autoSelectRole(key) {
//   if (key) {
//     router.push({
//       name: 'rolesManagement',
//       params: { roleId: key },
//     });
//   }
// }
function renderOrg(options) {
  const org = roleList.value[2].children.find(
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
    roleList.value[2].children.push({
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
function initRoleList() {
  roleList.value[0].children = [];
  roleList.value[1].children = [];
  roleList.value[2].children = [];
}
function renderRole() {
  axios.get('/v1/role').then((res) => {
    initRoleList();
    if (Array.isArray(res.data) && res.data.length) {
      res.data.forEach((item) => {
        let isActive = false;
        if (String(item.id) === window.atob(activeRole.value)) {
          isActive = true;
        }
        switch (item.type) {
          case 'public':
            if (isActive) {
              expandRole.value = ['public', window.btoa(item.id)];
            }
            roleList.value[0].children.push({
              info: item,
              prefix: renderIcon(User),
              label: item.name,
              key: window.btoa(item.id),
            });
            break;
          case 'group':
            if (isActive) {
              expandRole.value = [
                'group',
                window.btoa(`group-${item.group_id}`),
              ];
            }
            renderGroup(item);
            break;
          case 'org':
            if (isActive) {
              expandRole.value = ['org', window.btoa(`org-${item.org_id}`)];
            }
            renderOrg(item);
            break;
          default:
            break;
        }
      });
      // autoSelectRole(activeRole.value);
    }
  });
}
function getRoleList() {
  if (router.currentRoute.value.name === 'rolesManagement') {
    activeRole.value = router.currentRoute.value.params.roleId;
  } else {
    activeRole.value = '';
  }
  renderRole();
}

function selectRole(key, options) {
  if (options[0].children) {
    return;
  }
  [activeRole.value] = key;
  router.push({
    name: 'rolesManagement',
    params: { roleId: activeRole.value },
  });
}

function expandKey(keys) {
  expandRole.value = keys;
}
const roleCreateForm = ref();
function createRole() {
  roleCreateForm.value.show();
}
function submitCreateFrom({ data, type }) {
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
