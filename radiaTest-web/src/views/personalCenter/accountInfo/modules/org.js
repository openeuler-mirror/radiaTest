import { ref, reactive, h } from 'vue';

import { formatTime } from '@/assets/utils/dateFormatUtils.js';
import { storage } from '@/assets/utils/storageUtils';
import { state } from './userInfo';
import { changeLoadingStatus } from '@/assets/utils/loading';
import { NTag } from 'naive-ui';
import { setActiveOrgInfo } from './orgDrawer';
import { getUserInfo } from '@/api/get';

const showAddModal = ref(false);
const addInfo = reactive({ org: '', claEmail: '' });
const orgList = ref([]);
const orgNameRule = {
  trigger: ['blur', 'change'],
  required: true,
  message: '组织不能为空',
  validator() {
    if (addInfo.org) {
      return true;
    }
    return false;

  }
};
const claEmailRule = {
  trigger: ['blur'],
  required: true,
  validator() {
    if (addInfo.claEmail) {
      const emailReg = /^[A-Za-z0-9\u4e00-\u9fa5]+@[a-zA-Z0-9_-]+(\.[a-zA-Z0-9_-]+)+$/;
      if (!emailReg.test(addInfo.claEmail)) {
        return new Error('邮箱格式不对!');
      }
      return true;
    }
    return new Error('cla邮箱不能为空!');

  }
};
function init() {
  getUserInfo(storage.getValue('user_id')).then(res => {
    const { data } = res;
    state.userInfo = data;

  }).catch((err) => {
    window.$message?.error(err.data.error_msg || '未知错误');
    changeLoadingStatus(false);
  });
}
function handleAddOrg() {
  init();
  showAddModal.value = true;
}
const orgColumns = [
  {
    title: '组织名称',
    key: 'org_name',
    align: 'center',
  },
  {
    title: '组织描述',
    key: 'org_description',
    align: 'center',
  },
  {
    title: '创建时间',
    key: 're_user_org_create_time',
    align: 'center',
    render(row) {
      return h('span', null, [formatTime(new Date(row.re_user_org_create_time), 'yyyy-MM-dd hh:mm:ss')]);
    },
  },
  {
    title: 'cla邮箱',
    key: 'email',
    align: 'center',
    render(row) {
      return h('span', null, [row.re_user_org_cla_info.email]);
    }
  },
  {
    title: '角色',
    key: 'role',
    align: 'center',
    render(row) {
      const tag = h(
        NTag,
        {
          type: 'info',
        },
        row.role?.name
      );
      return tag;
    },
  },
];
const pagination = {
  pagesize: 5
};
function orgRowProps(row) {
  return {
    style: row.re_user_org_role_type === 2 ? 'cursor: pointer;' : 'cursor: not-allowed;',
    onClick: () => {
      if (row.re_user_org_role_type === 2) {
        setActiveOrgInfo(row);
      }
    },
  };
}

export {
  showAddModal,
  pagination,
  orgColumns,
  orgList,
  addInfo,
  orgNameRule,
  claEmailRule,
  init,
  handleAddOrg,
  orgRowProps
};
