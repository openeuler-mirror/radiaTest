import { ref, h } from 'vue';
import { NIcon } from 'naive-ui';

import router from '@/router/index';

import { LockClosedOutline, HomeOutline } from '@vicons/ionicons5';
import { BellOutlined } from '@vicons/antd';
import { Users } from '@vicons/tabler';
import { Organization24Regular } from '@vicons/fluent';

function renderIcon (icon) {
  return () => h(NIcon, null, {
    default: () => h(icon)
  });
}
const showHeader = ref(false);
const menuOptions = ref();
function initRoleOptions (roleType) {
  if (roleType === 1 || roleType === 2) {
    menuOptions.value = [
      {
        label: '组织管理',
        key: 'orgManagement',
        icon: renderIcon(Organization24Regular),
      },
      {
        label: '安全设置',
        key: 'setting',
        icon: renderIcon(LockClosedOutline),
        disabled: true,
      }
    ];
    showHeader.value = false;
  } else {
    menuOptions.value = [
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
        icon: renderIcon(BellOutlined),
      },
      {
        label: '安全设置',
        key: 'setting',
        icon: renderIcon(LockClosedOutline),
        disabled: true,
      }
    ];
    showHeader.value = true;
  }
}

function handleUpdateValue (key) {
  router.push({
    name: key
  });
}

const value = ref('');
const collapsed = ref(true);
const expandedKey = ref('');

export {
  value, showHeader, menuOptions, expandedKey, collapsed, handleUpdateValue, initRoleOptions
};
