import { ref } from 'vue';
import axios from '@/axios.js';
import { formatTime } from '@/assets/utils/dateFormatUtils.js';
import router from '@/router';
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
    rows: [
      {
        cols: [
          { label: '机器类型', value: '' },
          { label: '机器数量', value: '' },
        ],
      },
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
function getStatus() {
  axios.get('/v1/task/status').then((res) => {
    status.value = res.data;
  });
}
const report = ref({
  name: '',
  content: '',
});
// function getReport() {
//   axios.get(`/v1/tasks/${task.value.id}/reports`).then((res) => {
//     if (res.data.title && res.data.content) {
//       report.value.name = res.data.title;
//       report.value.content = res.data.content;
//     }
//   });
// }
// eslint-disable-next-line max-lines-per-function
function setDataList(Info) {
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
      rows: [
        {
          cols: [
            { label: '机器类型', value: Info.machine_type },
            { label: '机器数量', value: Info.machine_num },
          ],
        },
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
function getDetail(caseId) {
  axios
    .get(`/v1/baseline/${caseId}`)
    .then((res) => {
      axios
        .get('/v1/case', {
          id: res.data.case_id,
        })
        .then((response) => {
          [caseInfo.value] = response.data;
          caseInfo.value.title = res.data.title;
          if (response.data[0].git_repo?.framework?.id) {
            axios
              .get('/v1/framework', {
                id: response.data[0].git_repo.framework.id,
              })
              .then((result) => {
                [caseInfo.value.framework] = result.data;
                setDataList(caseInfo.value);
              });
          } else {
            setDataList(caseInfo.value);
          }
          if (!caseInfo.value.code) {
            caseInfo.value.code = '';
          }
        })
        .catch((err) => {
          window.$message?.error(err.data.error_msg || '未知错误');
        });
    })
    .catch(() => {
      router.push({ name: 'folderview' });
    });
  // axios.get(`/v1/case/${caseId}/task`).then((res) => {
  //   task.value = res.data;
  //   getReport();
  // });
  getStatus();
}
function setStatus(state) {
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

export {
  report,
  status,
  task,
  caseInfo,
  detailsList,
  showReportModal,
  getDetail,
  setStatus,
};
