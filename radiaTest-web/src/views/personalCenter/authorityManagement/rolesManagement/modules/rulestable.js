import { ref, h } from 'vue';
import { NIcon, NSpace, NSwitch } from 'naive-ui';
import { CheckmarkCircleOutline } from '@vicons/ionicons5';
import { Prohibited24Regular } from '@vicons/fluent';
import { changeLoadingStatus } from '@/assets/utils/loading';
import axios from '@/axios';
import { roleId, getRoleInfo } from './roleInfo';

const showDrawer = ref(false);
const roleInfo = ref({});
const ruleData = ref([]);
const ruleColumns = [
  {
    title: '名称',
    key: 'alias',
    align: 'center',
  },
  {
    title: '路由',
    key: 'uri',
    align: 'center',
  },
  {
    title: '请求方式',
    key: 'act',
    align: 'center',
  },
  {
    title: '规则类型',
    key: 'eft',
    align: 'center',
    render(row) {
      let [color, text, icon] = [];
      if (row.eft === 'allow') {
        color = 'green';
        text = '允许';
        icon = CheckmarkCircleOutline;
      } else {
        color = 'red';
        text = '拒绝';
        icon = Prohibited24Regular;
      }
      return h(
        'div',
        {
          style: `color:${color};display:flex;align-items:center;justify-content:center`,
        },
        [
          h(NIcon, null, {
            default: () => h(icon),
          }),
          text,
        ]
      );
    },
  },
];
function setDrawerStatus(status) {
  showDrawer.value = status;
}
function setRoleInfo(info) {
  roleInfo.value = info;
}
function setRuleData(data) {
  ruleData.value = data;
}
const ruleModal = ref();
function getOperateAction() {
  let actionUrl = '/v1/scope_role';
  if (roleInfo.value.type === 'group') {
    actionUrl = `/v1/scope_role/group/${roleInfo.value.group_id}`;
  } else if (roleInfo.value.type === 'org') {
    actionUrl = `/v1/scope_role/org/${roleInfo.value.org_id}`;
  }
  return actionUrl;
}
const relationRuleColumns = [
  {
    title: '名称',
    key: 'alias',
    align: 'center',
  },
  {
    title: '路由',
    key: 'uri',
    align: 'center',
  },
  {
    title: '请求方式',
    key: 'act',
    align: 'center',
  },
  {
    title: '规则类型',
    key: 'eft',
    align: 'center',
    render(row) {
      let [color, text, icon] = [];
      if (row.eft === 'allow') {
        color = 'green';
        text = '允许';
        icon = CheckmarkCircleOutline;
      } else {
        color = 'red';
        text = '拒绝';
        icon = Prohibited24Regular;
      }
      return h(
        'div',
        {
          style: `color:${color};display:flex;align-items:center;justify-content:center`,
        },
        [
          h(NIcon, null, {
            default: () => h(icon),
          }),
          text,
        ]
      );
    },
  },
  {
    title: '操作',
    key: 'action',
    className: 'cols operation',
    render: (row) => {
      let loading = false;
      const actionUrl = getOperateAction();
      return h(
        NSpace,
        {
          justify: 'center',
          align: 'center',
        },
        [
          h(
            NSwitch,
            {
              loading,
              value: row.allow,
              onUpdateValue: (value) => {
                const method = value ? 'post' : 'delete';
                loading = true;
                axios[method](actionUrl, {
                  scope_id: row.id,
                  role_id: Number(roleId.value),
                })
                  .then(() => {
                    loading = false;
                    row.allow = value;
                    getRoleInfo();
                  })
                  .catch((err) => {
                    loading = false;
                    window.$message?.error(err.data.error_msg || '未知错误');
                  });
              },
              railStyle: ({ checked }) => {
                const style = {};
                if (!checked) {
                  style.background = '#d03050';
                } else {
                  style.background = '#2080f0';
                }
                return style;
              },
            },
            {
              checked: () => '启用',
              unchecked: () => '关闭',
            }
          ),
        ]
      );
    },
  },
];
const relationRuleData = ref();
const relationRulePagination = {
  pageSize: 5,
};
function getRelationRules() {
  changeLoadingStatus(true);
  axios.get('/v1/scope').then((res) => {
    relationRuleData.value = res.data.map((item) => {
      item.allow = ruleData.value.findIndex((i) => i.id === item.id) !== -1;
      return { ...item };
    });
    changeLoadingStatus(false);
  });
}
function relationRule() {
  getRelationRules();
  ruleModal.value.show();
}
const rulePagination = {
  pageSize: 5,
};
export {
  relationRulePagination,
  relationRuleData,
  relationRuleColumns,
  rulePagination,
  showDrawer,
  setDrawerStatus,
  setRoleInfo,
  roleInfo,
  ruleColumns,
  setRuleData,
  ruleModal,
  ruleData,
  relationRule,
};
