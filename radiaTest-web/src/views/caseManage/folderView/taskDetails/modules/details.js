import { ref, h } from 'vue';
import axios from '@/axios.js';
import { createCaseReview } from '@/api/post';
import { formatTime } from '@/assets/utils/dateFormatUtils.js';
import router from '@/router';
import { NButton, NFormItem, NInput, NSpace } from 'naive-ui';
import { getCaseDetail } from '@/api/get';
import { expandNode } from '@/views/caseManage/folderView/modules/menu';
const source = ref([]);
const caseInfo = ref({});
const task = ref({});
const detailsList = ref([
  {
    title: '基础信息',
    name: 'baseInfo',
    rows: [
      {
        cols: [
          { label: '标题', value: '' },
          { label: '用例', value: '' },
        ],
      },
      {
        cols: [
          { label: '测试级别', value: '' },
          { label: '测试类型', value: '' },
        ],
      },
      {
        cols: [
          { label: '责任人', value: '' },
          { label: '创建时间', value: '' },
        ],
      },
      {
        cols: [
          { label: '修改人', value: '' },
          { label: '更新时间', value: '' },
        ],
      },
      { cols: [{ label: '是否自动化', value: '' }] },
    ],
  },
  {
    title: '用例详情',
    name: 'caseDetails',
    editTools: true,
    rows: [
      { cols: [{ label: '机器类型', value: '' }] },
      { cols: [{ label: '机器数量', value: '' }] },
      { cols: [{ label: '描述', value: '' }] },
      { cols: [{ label: '预置条件', value: '' }] },
      { cols: [{ label: '测试步骤', value: '' }] },
      { cols: [{ label: '预期结果', value: '' }] },
      { cols: [{ label: '备注', value: '' }] },
    ],
  },
  {
    title: '执行信息',
    name: 'info',
    rows: [
      {
        cols: [
          { label: '执行框架', value: '' },
          { label: '是否已适配', value: '' },
        ],
      },
      {
        cols: [
          { label: '代码仓', value: '' },
          { label: '相对路径', value: '' },
        ],
      },
    ],
  },
]);
const status = ref([]);
function getStatus () {
  axios.get('/v1/task/status').then((res) => {
    status.value = res.data;
  });
}
const report = ref({
  name: '',
  content: '',
});
// eslint-disable-next-line max-lines-per-function
function setDataList (Info) {
  detailsList.value = [
    {
      title: '基础信息',
      name: 'baseInfo',
      rows: [
        {
          cols: [
            { label: '标题', value: Info.title },
            { label: '用例', value: Info.name },
          ],
        },
        {
          cols: [
            { label: '测试级别', value: Info.test_level },
            { label: '测试类型', value: Info.test_type },
          ],
        },
        {
          cols: [
            { label: '责任人', value: Info.owner },
            { label: '是否自动化', value: Info.automatic ? '是' : '否' },
          ],
        },
        {
          cols: [
            {
              label: '创建时间',
              value: formatTime(Info.create_time, 'yyyy-MM-dd hh:mm:ss'),
            },
            {
              label: '更新时间',
              value: formatTime(Info.update_time, 'yyyy-MM-dd hh:mm:ss'),
            },
          ],
        },
      ],
    },
    {
      title: '用例详情',
      name: 'caseDetails',
      editTools: true,
      rows: [
        { cols: [{ label: '机器类型', value: Info.machine_type }] },
        { cols: [{ label: '机器数量', value: Info.machine_num }] },
        { cols: [{ label: '描述', value: Info.description, type: 'pre' }] },
        { cols: [{ label: '预置条件', value: Info.preset, type: 'pre' }] },
        { cols: [{ label: '测试步骤', value: Info.steps, type: 'pre' }] },
        { cols: [{ label: '预期结果', value: Info.expection, type: 'pre' }] },
        { cols: [{ label: '备注', value: Info.remark, type: 'pre' }] },
      ],
    },
    {
      title: '执行信息',
      name: 'info',
      rows: [
        {
          cols: [
            { label: '执行框架', value: Info.framework?.name },
            {
              label: '是否已适配',
              value: Info.framework?.adaptive ? '是' : '否',
            },
          ],
        },
        {
          cols: [
            { label: '代码仓', value: Info.framework?.url },
            { label: '相对路径', value: Info.framework?.logs_path },
          ],
        },
      ],
    },
  ];
}
const loading = ref(false);
function getDetail (caseId) {
  loading.value = true;
  axios
    .get(`/v1/baseline/${caseId}`)
    .then((res) => {
      source.value = res.data.source;
      getCaseDetail(res.data.case_id) 
        .then((response) => {
          caseInfo.value = response.data;
          caseInfo.value.title = res.data.title;
          if (response.data.git_repo?.framework?.id) {
            axios
              .get(`/v1/framework/${response.data.git_repo.framework.id}`)
              .then((result) => {
                caseInfo.value.framework = result.data;
                setDataList(caseInfo.value);
              });
          } else {
            setDataList(caseInfo.value);
          }
          if (!caseInfo.value.code) {
            caseInfo.value.code = '';
          }
          loading.value = false;
        })
        .catch((err) => {
          loading.value = false;
          window.$message?.error(err.data.error_msg || '未知错误');
        });
    })
    .catch(() => {
      router.push({ name: 'folderview' });
    });
  getStatus();
}
function setStatus (state) {
  const index = status.value.findIndex((item) => item.id === state.id);
  const active = status.value.findIndex(
    (item) => item.id === task.value.status_id
  );
  if (index === active) {
    return 'process';
  }
  return index > active ? 'wait' : 'finish';
}
const showReportModal = ref(false);
const editInfo = {
  machine_type: {
    index: 0,
    colsIndex: 0
  },
  case_description: {
    index: 2,
    colsIndex: 0
  },
  machine_num: {
    index: 1,
    colsIndex: 0
  },
  preset: {
    index: 3,
    colsIndex: 0
  },
  steps: {
    index: 4,
    colsIndex: 0
  },
  expectation: {
    index: 5,
    colsIndex: 0
  },
  remark: {
    index: 6,
    colsIndex: 0
  },
};
function getFormData (data) {
  const result = {};
  const keys = Object.keys(editInfo);
  for (const key of keys) {
    const element = editInfo[key];
    result[key] = data[element.index].cols[element.colsIndex].value;
  }
  return result;
}
const caseReviewTitle = ref('');
const titleRule = {
  trigger: ['input', 'blur'],
  message: '请填写标题',
  validator () {
    if (caseReviewTitle.value !== '') {
      return true;
    }
    return false;
  }
};
const caseReviewDescription = ref('');
function dialogContent () {
  return h('div', null, [
    h(NFormItem, {
      label: '标题',
      rule: titleRule,
    }, h(NInput, {
      value: caseReviewTitle.value,
      onUpdateValue: value => {
        caseReviewTitle.value = value;
      },
    })),
    h(NFormItem, {
      label: '描述',
    }, h(NInput, {
      value: caseReviewDescription.value,
      onUpdateValue: value => {
        caseReviewDescription.value = value;
      },
    }))
  ]);
}
function updateDetail ({ data }) {
  const d = window.$dialog?.info({
    title: '补充信息',
    content: dialogContent,
    action: () => {
      return h(NSpace, null, [
        h(NButton, {
          size: 'large',
          type: 'error',
          ghost: true,
          onClick: () => {
            d.destroy();
            getDetail(router.currentRoute.value.params.taskid);
          }
        }, '取消'),
        h(NButton, {
          size: 'large',
          type: 'primary',
          ghost: true,
          onClick: () => {
            if (titleRule.validator()) {
              createCaseReview({
                ...getFormData(data),
                title: caseReviewTitle.value,
                description: caseReviewDescription.value,
                case_detail_id: router.currentRoute.value.params.taskid,
                source: source.value,
                case_mod_type: 'edit'
              }).then(() => d.destroy());
            } else {
              window.$message?.error('请检查填写信息!');
            }
          }
        }, '确认')
      ]);
    }
  });
}
function cancelDetail () {
  if (router.currentRoute.value.params.taskid !== 'development') {
    getDetail(router.currentRoute.value.params.taskid);
  }
}
const editInfoValue = ref();
const modifyModal = ref();
function edit (index) {
  editInfoValue.value = {
    ...getFormData(detailsList.value[index].rows),
    description: '',
    title: '',
    case_detail_id: caseInfo.value.id,
  };
  modifyModal.value.show();
}
function editSubmit (formValue) {
  createCaseReview({
    ...formValue,
    source: source.value,
    case_mod_type: 'edit'
  }).then(() => {
    modifyModal.value.close();
    expandNode(router.currentRoute.value.params.taskid);
  });
}
export {
  editInfoValue,
  modifyModal,
  loading,
  report,
  status,
  caseReviewTitle,
  caseReviewDescription,
  task,
  caseInfo,
  detailsList,
  showReportModal,
  getDetail,
  setStatus,
  updateDetail,
  source,
  cancelDetail,
  edit,
  editSubmit
};
