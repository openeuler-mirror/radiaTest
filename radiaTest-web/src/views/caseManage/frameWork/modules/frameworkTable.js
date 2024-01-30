import { ref, h } from 'vue';
import { NSpace, NButton, NIcon } from 'naive-ui';
import { renderTooltip } from '@/assets/render/tooltip';
import { Construct, CheckmarkCircleOutline } from '@vicons/ionicons5';
import { Delete24Regular as Delete, Prohibited24Regular } from '@vicons/fluent';
import { isCreate, showForm, changeFramework, frameworkForm, deleteFramework } from './frameWorkAction';
import axios from '@/axios';
import { workspace } from '@/assets/config/menu.js';
import { getFramework as getFrameworkList } from '@/api/get';


const frameLoading = ref(false);
function getRepo(row) {
  axios
    .get(`/v1/ws/${workspace.value}/git-repo`, { framework_id: row.id })
    .then((res) => {
      row.expand = true;
      frameLoading.value = false;
      row.expandData = res.data.map((item) => ({ ...item, frameworkRow: row }));
    })
    .catch((err) => {
      frameLoading.value = false;
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}
const frameworkData = ref([]); // 框架数据
const frameworkFilterData = ref([]); // 框架筛选数据

const frameworkColumns = [
  {
    title: '框架名称',
    key: 'name',
    align: 'center'
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
          target: '_blank'
        },
        row.url
      );
    }
  },
  {
    title: '日志目录相对路径',
    key: 'logs_path',
    align: 'center'
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
          style: `color:${color};display:flex;align-items:center;justify-content:center`
        },
        [
          h(NIcon, null, {
            default: () => h(icon)
          }),
          text
        ]
      );
    }
  },
  {
    title: '操作',
    key: 'action',
    align: 'center',
    className: 'cols operation',
    render: (row) => {
      return h(
        NSpace,
        {
          justify: 'center',
          align: 'center'
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
                }
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
                }
              },
              h(NIcon, { size: '20' }, h(Delete))
            ),
            '删除'
          )
        ]
      );
    }
  }
];
function frameRowProps(row) {
  return {
    onClick: (e) => {
      const isTrigger = e.path.some((item) => item?.classList?.contains('n-data-table-expand-trigger'));
      if (!row.expand && isTrigger) {
        frameLoading.value = true;
        getRepo(row, frameLoading);
      }
    }
  };
}
// let frameworkId ;
function getFramework() {
  getFrameworkList().then((res) => {
    frameworkData.value = res.data.map((item) => {
      return {
        ...item,
        expand: false
      };
    });
    frameworkFilterData.value = frameworkData.value;
  });
}

function initData() {
  getFramework();
}

const filterRule = ref([
  {
    path: 'name',
    name: '框架名称',
    type: 'input'
  },
  {
    path: 'url',
    name: '仓库地址',
    type: 'input'
  },
  {
    path: 'logs_path',
    name: '日志地址',
    type: 'input'
  },
  {
    path: 'adaptive',
    name: '适配',
    type: 'select',
    options: [
      { label: '是', value: 'true' },
      { label: '否', value: 'false' }
    ]
  }
]);

const filterchange = (filterArray) => {
  frameworkFilterData.value = frameworkData.value;
  filterArray.forEach((v) => {
    frameworkFilterData.value = frameworkFilterData.value.filter((v2) => {
      if (v.value) {
        return v2[v.path]
          .toString()
          .toLowerCase()
          .includes(v.value.toString().toLowerCase());
      }
      return true;
    });
  });
};

export {
  frameLoading,
  frameworkFilterData,
  frameworkColumns,
  initData,
  frameRowProps,
  getFramework,
  getRepo,
  filterRule,
  filterchange
};
