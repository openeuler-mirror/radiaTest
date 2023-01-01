import { ref, h } from 'vue';
import { NIcon, NButton, NSpace } from 'naive-ui';
import { CheckmarkCircleOutline } from '@vicons/ionicons5';
import { Delete24Regular as Delete, Prohibited24Regular } from '@vicons/fluent';
import { renderTooltip } from '@/assets/render/tooltip';
import axios from '@/axios';
import { changeLoadingStatus } from '@/assets/utils/loading';
import { unkonwnErrorMsg } from '@/assets/utils/description';

const data = ref();
const pagination = ref({
  page: 1,
  pageSize: 10,
  pageCount: 1,
  showSizePicker: true,
  pageSizes: [5, 10, 20, 50]
});

function getRules(options) {
  changeLoadingStatus(true);
  axios.get('/v1/scope', {
    ...options,
    page_num: pagination.value.page,
    page_size: pagination.value.pageSize,
  })
    .then((res) => {
      data.value = res.data?.items || [];
      pagination.value.pageCount = res.data?.pages || 1;
      changeLoadingStatus(false);
    }).catch((err) => {
      window.$notification?.error({ content: err.data.error_msg || unkonwnErrorMsg });
      changeLoadingStatus(false);
    });
}

const pageChange = (page) => {
  pagination.value.page = page;
  getRules();
};
const pageSizeChange = (pageSize) => {
  pagination.value.pageSize = pageSize;
  pagination.value.page = 1;
  getRules();
};

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
  getRules(options);
}

export { 
  filters, 
  data, 
  columns, 
  pagination,
  pageChange,
  pageSizeChange,
  getRules, 
  filterChange 
};
