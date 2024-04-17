import { ref, h } from 'vue';
import { NIcon } from 'naive-ui';

import router from '@/router/index';

import { LockClosedOutline, HomeOutline } from '@vicons/ionicons5';
import { BellOutlined } from '@vicons/antd';
import { Users, Settings } from '@vicons/tabler';
import { Organization24Regular, Password24Regular } from '@vicons/fluent';
import { ManageAccountsOutlined } from '@vicons/material';
import { Users as faUsers } from '@vicons/fa';

function renderIcon(icon) {
  return () =>
    h(NIcon, null, {
      default: () => h(icon)
    });
}
const showHeader = ref(false);
const menuOptions = ref();
const adminMenu = [
  {
    label: '组织管理',
    key: 'orgManagement',
    icon: renderIcon(Organization24Regular)
  },
  {
    label: '权限管理',
    key: 'authorityManagement',
    icon: renderIcon(ManageAccountsOutlined)
  },
  {
    label: '成员管理',
    key: 'usersManagement',
    icon: renderIcon(faUsers)
  },
  {
    label: '配置管理',
    key: 'configManagement',
    icon: renderIcon(Settings)
  },
  {
    label: '弱口令设置',
    key: 'weakPasswordSetting',
    icon: renderIcon(Password24Regular),
  },
  {
    label: '安全设置',
    key: 'securitySetting',
    icon: renderIcon(LockClosedOutline),
  }
];
const adminResetPwdMenu = [
  {
    label: '安全设置',
    key: 'securitySetting',
    icon: renderIcon(LockClosedOutline),
  }
];
const userMenu = [
  {
    label: '用户信息',
    key: 'accountInfo',
    icon: renderIcon(HomeOutline)
  },
  {
    label: '用户组管理',
    key: 'accountManagement',
    icon: renderIcon(Users)
  },
  {
    label: '消息中心',
    key: 'news',
    icon: renderIcon(BellOutlined)
  },
  {
    label: '权限管理',
    key: 'authorityManagement',
    icon: renderIcon(ManageAccountsOutlined)
  },
];
function initRoleOptions(roleType) {
  if (roleType === 1) {
    menuOptions.value = adminMenu;
    showHeader.value = false;
  } else if (roleType === 'resetPassword') {
    menuOptions.value = adminResetPwdMenu;
    showHeader.value = false;
  } else {
    menuOptions.value = userMenu;
    showHeader.value = true;
  }
}

function handleUpdateValue(key) {
  router.push({
    name: key
  });
}

const value = ref('');
const collapsed = ref(true);
const expandedKey = ref('');

export { value, showHeader, menuOptions, expandedKey, collapsed, handleUpdateValue, initRoleOptions };
