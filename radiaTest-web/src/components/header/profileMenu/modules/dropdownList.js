import { h, ref } from 'vue';
import { NIcon } from 'naive-ui';
import { HomeOutlined } from '@vicons/antd';
import { Exit } from '@vicons/ionicons5';

import { activeOrg, getOrg } from './orgInfo';
import axios from '@/axios';
import router from '@/router/index';

const options = [
  {
    label: '用户中心',
    key: 'accountInfo',
    icon() {
      return h(NIcon, null, {
        default: () => h(HomeOutlined)
      });
    }
  },
  {
    label: '退出登录',
    key: 'exit',
    props: {
      style: {
        display: window.hideLogout ? 'none' : ''
      }
    },
    icon() {
      return h(NIcon, null, {
        default: () => h(Exit)
      });
    }
  }
];

const iframeOptions = [
  {
    label: '用户中心',
    key: 'accountInfo',
    icon() {
      return h(NIcon, null, {
        default: () => h(HomeOutlined)
      });
    }
  }
];

const orgRule = {
  trigger: ['blur', 'change'],
  validator() {
    if (activeOrg.value) {
      return true;
    }
    return new Error('组织不能为空');
  }
};
const showOrgModal = ref(false);

function handleSelect(key) {
  if (key === 'accountManagement') {
    getOrg();
    showOrgModal.value = true;
  } else if (key === 'exit') {
    axios.delete('/v1/logout').then((res) => {
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

export { options, iframeOptions, orgRule, showOrgModal, handleSelect };
