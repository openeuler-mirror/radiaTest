import { h, ref } from 'vue';
import { NIcon } from 'naive-ui';
import { HomeOutlined } from '@vicons/antd';
import { Exit } from '@vicons/ionicons5';

import { activeOrg, orgOptions, currentOrg, getOrg } from './orgInfo';
import axios from '@/axios';
import { storage } from '@/assets/utils/storageUtils';
import router from '@/router/index';

const options = [
  {
    label: '用户中心',
    key: 'accountInfo',
    icon () {
      return h(NIcon, null, {
        default: () => h(HomeOutlined)
      });
    },
  },
  {
    label: '退出登陆',
    key: 'exit',
    props: {
      style: {
        display: window.hideLogout ? 'none' : '',
      }
    },
    icon () {
      return h(NIcon, null, {
        default: () => h(Exit)
      });
    }
  },
];

const iframeOptions = [
  {
    label: '用户中心',
    key: 'accountInfo',
    icon () {
      return h(NIcon, null, {
        default: () => h(HomeOutlined)
      });
    },
  }
];

const orgRule = {
  trigger: ['blur', 'change'],
  validator () {
    if (activeOrg.value) {
      return true;
    }
    return new Error('组织不能为空');
  }
};
const showOrgModal = ref(false);
function switchOrg () {
  if (orgRule.validator() === true) {
    axios.put(`/v1/users/org/${activeOrg.value}`).then(res => {
      if (res.error_code === '2000') {
        window.$message?.success('切换成功!');
        storage.setValue('orgId', activeOrg.value);
        const current = orgOptions.value.find(item => {
          return item.value === activeOrg.value;
        });
        currentOrg.value = current.label;
        showOrgModal.value = false;
        router.replace({ name: 'home' });
        document.dispatchEvent(new CustomEvent('reloadInfo'));
      }
    });
  } else {
    window.$message?.error('填写信息有误!');
    showOrgModal.value = false;
  }
}
function handleSelect (key) {
  if (key === 'accountManagement') {
    getOrg();
    showOrgModal.value = true;
  } else if (key === 'exit') {
    axios.delete('/v1/logout').then(res => {
      if (res.error_code === '2000') {
        router.replace({
          name: 'login'
        });
      }
    });
  } else if (key === 'accountInfo') {
    router.push({ name: key });
  }
}

export {
  options,
  iframeOptions,
  orgRule,
  showOrgModal,
  switchOrg,
  handleSelect,
};
