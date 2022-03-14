import { ref, h } from 'vue';
import { NIcon, NButton, NSpace } from 'naive-ui';
import { CheckmarkCircleOutline } from '@vicons/ionicons5';
import { Delete24Regular as Delete, Prohibited24Regular } from '@vicons/fluent';
import { renderTooltip } from '@/assets/render/tooltip';
import axios from '@/axios';
// import { setFormType, createRef, setEditData } from './ruleForm';
import { changeLoadingStatus } from '@/assets/utils/loading';

const data = ref();
const pagination = {
  pageSize: 10,
};
function getRules() {
  changeLoadingStatus(true);
  axios.get('/v1/scope').then((res) => {
    data.value = res.data;
    changeLoadingStatus(false);
  });
}
// function editRule(row) {
//   setFormType('edit');
//   setEditData(JSON.parse(JSON.stringify(row)));
//   createRef.value.show();
// }
function deleteRule(row) {
  axios.delete(`/v1/scope/${row.id}`).then(() => getRules());
}
const columns = [
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
      return h(
        NSpace,
        {
          justify: 'center',
          align: 'center',
        },
        [
          // renderTooltip(
          //   h(
          //     NButton,
          //     {
          //       size: 'medium',
          //       type: 'warning',
          //       circle: true,
          //       onClick: () => editRule(row),
          //     },
          //     h(NIcon, { size: '20' }, h(Construct))
          //   ),
          //   '修改'
          // ),
          renderTooltip(
            h(
              NButton,
              {
                size: 'medium',
                type: 'error',
                circle: true,
                onClick: () => {
                  deleteRule(row);
                },
              },
              h(NIcon, { size: '20' }, h(Delete))
            ),
            '删除'
          ),
        ]
      );
    },
  },
];
const filters = [
  { key: 'alias', placeholder: '请输入名称', type: 'input' },
  { key: 'uri', placeholder: '请输入路由', type: 'input' },
  {
    key: 'act',
    placeholder: '请选择请求方式',
    type: 'select',
    options: [
      { label: 'get', value: 'get' },
      { label: 'post', value: 'post' },
      { label: 'delete', value: 'delete' },
      { label: 'put', value: 'put' },
    ],
  },
  {
    key: 'eft',
    placeholder: '请选择规则类型',
    type: 'select',
    options: [
      { label: '允许', value: 'allow' },
      { label: '拒绝', value: 'deny' },
    ],
  },
];

function filterChange(options) {
  axios.get('/v1/scope', options).then((res) => {
    data.value = res.data;
  });
}

export { filters, data, columns, pagination, getRules, filterChange };
