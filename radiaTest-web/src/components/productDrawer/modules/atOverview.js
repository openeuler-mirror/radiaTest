import { h, ref } from 'vue';
import { getAtOverview } from '@/api/get';
import customProgress from '@/components/customProgress/customProgress';
import { NIcon, NTag, NTooltip } from 'naive-ui';
import { Circle24Filled } from '@vicons/fluent';

function renderResColor (resStatus, failmodule) {
  if (!typeof(resStatus) === String) {
    return 'white';
  }

  switch(true) {
    case resStatus.startsWith('schedule') || resStatus === 'running':
      return '#2080F0';
    case resStatus === 'Done: passed' && failmodule === '-':
      return '#18A058';
    case resStatus.endsWith('skipped') || resStatus === 'cancelled':
      return '#F0F0F0';
    case resStatus === 'Done: incomplete':
      return '#f88a8a';
    default:
      return '#c20000';
  }
}

const totalNum = ref(0);
const atGroupOverviewData = ref([]);
const atTestsOverviewData = ref([]);
const atLoading = ref(false);
const currentBuild = ref();

const atTestsOverviewShow = ref(false);

const atColumns = [
  {
    title: '构建记录',
    key: 'build',
    render: (row) => h(
      'p', 
      null,
      [
        h('span', null, row.build),
        h('span', null, row.build_time)
      ]
    ),
    sorter:  true
  },
  {
    title: '测试进展',
    key: 'progress',
    className: 'at-progress',
    render: (row) => {
      return h(
        customProgress, 
        { 
          progress: row
        }
      );
    }
  },
];

function handleUrlClick(url) {
  window.open(url);
}

const atTestsColumns = [
  {
    title: '测试项',
    key: 'test',
  },
  {
    title: 'aarch64',
    key: 'aarch64',
    className: 'tests-col',
    render: (row) => {
      if (row.aarch64_res_status === '-') { return row.aarch64_res_status; }
      if (row.aarch64_failedmodule_name !== '-') {
        return h('span', { class: 'tests-res' }, [
          h(NTooltip, { trigger: 'hover' }, {
            default: () => row.aarch64_res_status,
            trigger: () => h(
              NIcon,
              {
                size: 14,
                color: renderResColor(row.aarch64_res_status, row.aarch64_failedmodule_name),
                style: { cursor: 'pointer' },
                onClick: () => handleUrlClick(row.aarch64_res_log),
              },
              { default: () => h(Circle24Filled) }
            )
          }),
          h(
            NTag, 
            { 
              type: 'error', 
              size: 'small', 
              style: { cursor: 'pointer' },
              onClick: () => handleUrlClick(row.aarch64_failedmodule_log) 
            }, 
            row.aarch64_failedmodule_name
          )
        ]);
      }
      return h(
        NTooltip,
        { trigger: 'hover' },
        {
          default: () => row.aarch64_res_status,
          trigger: () => h(
            NIcon,
            {
              size: 14,
              color: renderResColor(row.aarch64_res_status, row.aarch64_failedmodule_name),
              style: { cursor: 'pointer' },
              onClick: () => handleUrlClick(row.aarch64_res_log),
            },
            { default: () => h(Circle24Filled) }
          )
        }
      );
    }
  },
  {
    title: 'x86_64',
    key: 'x86_64',
    className: 'tests-col',
    render: (row) => {
      if (row.x86_64_res_status === '-') { return row.x86_64_res_status; }
      if (row.x86_64_failedmodule_name !== '-') {
        return h('span', { class: 'tests-res' }, [
          h(NTooltip, { trigger: 'hover' }, {
            default: () => row.x86_64_res_status,
            trigger: () => h(
              NIcon,
              {
                size: 14,
                style: { cursor: 'pointer' },
                color: renderResColor(row.x86_64_res_status, row.x86_64_failedmodule_name),
                onClick: () => handleUrlClick(row.x86_64_res_log),
              },
              { default: () => h(Circle24Filled) }
            )
          }),
          h(
            NTag, 
            { 
              type: 'error', 
              size: 'small', 
              style: { cursor: 'pointer' },
              onClick: () => handleUrlClick(row.x86_64_failedmodule_log) 
            }, 
            row.x86_64_failedmodule_name
          )
        ]);
      }
      return h(
        NTooltip,
        { trigger: 'hover' },
        {
          default: () => row.x86_64_res_status,
          trigger: () => h(
            NIcon,
            {
              size: 14,
              color: renderResColor(row.x86_64_res_status, row.x86_64_failedmodule_name),
              style: { cursor: 'pointer' },
              onClick: () => handleUrlClick(row.x86_64_res_log),
            },
            { default: () => h(Circle24Filled) }
          )
        }
      );
    }
  },
];

function getAtData(id, params) {
  atLoading.value = true;
  getAtOverview(id, params)
    .then((res) => {
      if (!params.build_name) {
        atGroupOverviewData.value = res.data;
        if (atGroupOverviewData.value) {
          totalNum.value = res.total_num;
        }
      } else {
        atTestsOverviewData.value = res.data;
      }
    })
    .finally(() => {
      atLoading.value = false;
    });
}

function cleanData() {
  atGroupOverviewData.value = [];
  atTestsOverviewData.value = [];
  totalNum.value = 0;
  atTestsOverviewShow.value = false;
}

function handleAtBuildClick(id, rowData) {
  currentBuild.value = rowData.build;
  atTestsOverviewShow.value = true;
  getAtData(id, { build_name: rowData.build });
}

function handleTestsClose() {
  atTestsOverviewShow.value = false;
  atTestsOverviewData.value = [];
}

export {
  handleTestsClose,
  handleAtBuildClick,
  cleanData,
  currentBuild,
  atTestsOverviewShow,
  atGroupOverviewData,
  atTestsOverviewData,
  atLoading,
  getAtData,
  atColumns,
  atTestsColumns,
  totalNum,
};

