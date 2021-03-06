import { ref, h } from 'vue';
import { NSpace, NButton, NIcon } from 'naive-ui';
import { renderTooltip } from '@/assets/render/tooltip';
import { Construct, CheckmarkCircleOutline } from '@vicons/ionicons5';
import { Delete24Regular as Delete, Prohibited24Regular } from '@vicons/fluent';
import {
  isCreate,
  showForm,
  changeFramework,
  frameworkForm,
  deleteFramework,
} from './frameWorkAction';
import axios from '@/axios';
const frameLoading = ref(false);
function getRepo(row) {
  axios
    .get('/v1/git-repo', { framework_id: row.id })
    .then((res) => {
      row.expand = true;
      frameLoading.value = false;
      row.expandData = res.data.map((item) => ({...item,frameworkRow:row}));
    })
    .catch((err) => {
      frameLoading.value = false;
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}
const frameworkData = ref([]);

const frameworkColumns = [
  {
    title: '框架名称',
    key: 'name',
    align: 'center',
  },
  {
    title: '仓库地址',
    key: 'url',
    align: 'center',
    render(row) {
      return h(
        'a',
        {
          href: row.url,
          target: '_blank',
        },
        row.url
      );
    },
  },
  {
    title: '日志目录相对路径',
    key: 'logs_path',
    align: 'center',
  },
  {
    title: '是否已适配',
    key: 'adaptive',
    align: 'center',
    render(row) {
      let [color, text, icon] = [];
      if (row.adaptive) {
        color = 'green';
        text = '是';
        icon = CheckmarkCircleOutline;
      } else {
        color = 'red';
        text = '否';
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
                type: 'warning',
                circle: true,
                onClick: () => {
                  changeFramework(row.id);
                  frameworkForm.value.adaptive = row.adaptive;
                  frameworkForm.value.name = row.name;
                  frameworkForm.value.url = row.url;
                  frameworkForm.value.logs_path = row.logs_path;
                  isCreate.value = false;
                  showForm();
                },
              },
              h(NIcon, { size: '20' }, h(Construct))
            ),
            '修改'
          ),
          renderTooltip(
            h(
              NButton,
              {
                size: 'medium',
                type: 'error',
                circle: true,
                onClick: () => {
                  deleteFramework(row.id);
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
function frameRowProps(row) {
  return {
    onClick: (e) => {
      const isTrigger = e.path.some((item) =>
        item?.classList?.contains('n-data-table-expand-trigger')
      );
      if (!row.expand && isTrigger) {
        frameLoading.value = true;
        getRepo(row,frameLoading);
      }
    },
  };
}
// let frameworkId ;
function getFramework() {
  axios.get('/v1/framework').then((res) => {
    frameworkData.value = res.data.map((item) => {
      return {
        ...item,
        expand: false,
      };
    });
  });
}
function initData() {
  
  getFramework();
}
const frameworkPagination = ref({ pageSize: 10 });

export {
  frameLoading,
  frameworkPagination,
  frameworkData,
  frameworkColumns,
  initData,
  frameRowProps,
  getFramework,
  getRepo
};
