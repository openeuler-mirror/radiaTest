import axios from '@/axios';
import { ref } from 'vue';
import { renderIcon } from '@/assets/utils/icon';
import { GroupsFilled } from '@vicons/material';
import { Organization20Regular } from '@vicons/fluent';
import { getUserInfo } from './userInfo';
import { storage } from '@/assets/utils/storageUtils';

const selectdRole = ref('');
const expandKeys = ref([]);
const roleMenu = ref([
  {
    label: '公共角色',
    key: 'public',
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
function getGroups(orgs) {
  const groupIndex = roleMenu.value.findIndex((item) => item.key === 'group');
  roleMenu.value[groupIndex].children = [];
  const requests = orgs?.map((item) =>
    axios.get(`/v1/org/${item}/groups`, { page_num: 1, page_size: 99999 })
  );
  Promise.allSettled(requests).then((values) => {
    values?.forEach((res) => {
      if (res.status === 'fulfilled') {
        res.value.data?.items?.forEach((item) => {
          roleMenu.value[groupIndex].children.push({
            key: window.btoa(`group-${item.id}`),
            label: item.name,
            prefix: renderIcon(GroupsFilled),
          });
        });
      }
    });
  });
}
function getOrgs() {
  if (storage.getValue('role') === 1) {
    roleMenu.value = [
      {
        label: '平台',
        key: 'public',
      },
      {
        label: '团队',
        key: 'group',
        children: [],
      },
      {
        label: '组织',
        key: 'org',
        children: [],
      },
    ];
  } else {
    roleMenu.value = [
      {
        label: '团队',
        key: 'group',
        children: [],
      },
      {
        label: '组织',
        key: 'org',
        children: [],
      },
    ];
  }
  axios.get('/v1/orgs/all', { page_num: 1, page_size: 99999 }).then((res) => {
    const orgs = [];
    const groupInext = roleMenu.value.findIndex((item) => item.key === 'org');
    roleMenu.value[groupInext].children = res.data.items?.map((item) => {
      orgs.push(item.id);
      return {
        key: window.btoa(`org-${item.id}`),
        label: item.name,
        prefix: renderIcon(Organization20Regular),
      };
    });
    getGroups(orgs);
  });
}
function getMenu() {
  getOrgs();
}

function selectKey([key], option) {
  const [info] = option;
  const notVaildKeys = ['group', 'org'];
  if (info.children || notVaildKeys.includes(key)) {
    return;
  }
  selectdRole.value = key;
  getUserInfo();
}
function handleExpand(keys) {
  expandKeys.value = keys;
}
export { expandKeys, selectdRole, roleMenu, getMenu, selectKey, handleExpand };
