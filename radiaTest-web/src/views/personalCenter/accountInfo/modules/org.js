import { ref, reactive, h } from 'vue';

import axios from '@/axios';
import { formatTime } from '@/assets/utils/dateFormatUtils.js';
import { storage } from '@/assets/utils/storageUtils';
import { state } from './userInfo';
import { changeLoadingStatus } from '@/assets/utils/loading';

const showAddModal = ref(false);
const addInfo = reactive({ org: '', claEmail: '' });
const orgList = ref([]);
const orgNameRule = {
  trigger: ['blur', 'change'],
  required: true,
  message: '组织不能为空',
  validator () {
    if (addInfo.org) {
      return true;
    }
    return false;

  }
};
const claEmailRule = {
  trigger: ['blur'],
  required: true,
  validator () {
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
function init () {
  let hasOrg = '';
  axios.get(`/v1/users/${storage.getValue('gitee_id')}`).then(res => {
    const { data } = res;
    state.userInfo = data;
    data.orgs.forEach(item => {
      hasOrg += (`${item.org_id},`);
    });
    axios.get('/v1/org/cla', { has_org_ids: hasOrg.slice(0, hasOrg.length) }).then(response => {
      changeLoadingStatus(false);
      if (response.error_code === '2000') {
        orgList.value = response.data.map(item => {
          return {
            label: item.organization_name,
            value: item.organization_id
          };
        });
      }
    });
  }).catch((err) => {
    window.$message?.error(err.data.error_msg || '未知错误');
    changeLoadingStatus(false);
  });
}
function submitAddOrg () {
  if (claEmailRule.validator() && typeof claEmailRule.validator() !== 'object' && orgNameRule.validator()) {
    axios.post(`/v1/org/${addInfo.org}/cla`, {
      cla_verify_params: JSON.stringify({ email: addInfo.claEmail, }),
    }).then(res => {
      if (res.error_code === '4010') {
        window.$message?.warning('请先签署CLA');
      } else if (res.error_code === '2000') {
        window.$message?.success('添加成功');
        showAddModal.value = false;
        init();
      }
    });
  } else {
    window.$message?.error('请填写相关信息');
  }
}
function handleAddOrg () {
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
    render (row) {
      return h('span', null, [formatTime(new Date(row.re_user_org_create_time), 'yyyy-MM-dd hh:mm:ss')]);
    },
  },
  {
    title: 'cla邮箱',
    key: 'email',
    align: 'center',
    render (row) {
      return h('span', null, [row.re_user_org_cla_info.email]);
    }
  }
];
const pagination = {
  pagesize: 5
};

export {
  showAddModal,
  pagination,
  orgColumns,
  orgList,
  addInfo,
  orgNameRule,
  claEmailRule,
  submitAddOrg,
  init,
  handleAddOrg,
};
