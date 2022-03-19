import { ref, watch, computed } from 'vue';
import axios from '@/axios';
import { any2standard } from '@/assets/utils/dateFormatUtils';

const active = ref(false);
const title = ref('');
const selectedCase = ref('');
const selectedRecord = ref(null);
const jobId = ref(null);
const milestoneId = ref(null);
const originAnalyzeds = ref([]);
const originRecords = ref([]);
const logsData = ref([]);
const caseDetail = ref([]);
const successCheck = ref(true);
const failCheck = ref(true);
const searchCaseValue = ref(null);
const updateModalRef = ref(null);
const updateFormRef = ref(null);

const recordsTimeRange = ref([0, Date.now()]);
const failRecordsOnly = ref(false);
const sameMilestoneOnly = ref(false);

const analyzeds = computed(() =>
  originAnalyzeds.value.filter((item) => {
    return (
      (!searchCaseValue.value ||
        item.case.name.indexOf(searchCaseValue.value) !== -1) &&
      ((item.result === 'success' && successCheck.value) ||
        (item.result === 'fail' && failCheck.value))
    );
  })
);

const records = computed(() =>
  originRecords.value
    .filter((item) => {
      if (failRecordsOnly.value && item.result !== 'fail') {
        return false;
      }
      if (sameMilestoneOnly.value && item.milestone_id !== milestoneId.value) {
        return false;
      }
      if (!recordsTimeRange.value) {
        return true;
      }
      if (
        new Date(item.create_time).getTime() > recordsTimeRange.value[1] ||
        new Date(item.create_time).getTime() < recordsTimeRange.value[0]
      ) {
        return false;
      }
      return true;
    })
    .sort((rowA, rowB) => {
      if (rowA.create_time <= rowB.create_time) {
        return 1;
      }
      return -1;
    })
);

watch(active, () => {
  if (active.value === false) {
    originAnalyzeds.value = [];
    logsData.value = [];
    selectedCase.value = '';
    selectedRecord.value = null;
    originRecords.value = [];
  }
});

const getCases = (id) => {
  if (active.value === true) {
    axios
      .get('/v1/analyzed', { job_id: id })
      .then((res) => {
        if (res.data.length === 0) {
          active.value = false;
          window.$message?.error(
            '无法获取本测试任务的分析数据，请联系管理员进行处理'
          );
        } else {
          const tmpList = [];
          res.data.forEach((item) => {
            if (!tmpList.includes(item.case)) {
              tmpList.push(item.case);
              originAnalyzeds.value.push(item);
            }
          });
        }
      })
      .catch(() => {
        active.value = false;
        window.$message?.error('无法获取本测试任务的分析数据，请检查网络连接');
      });
  }
};

const getCaseDetail = (_case) => {
  axios
    .get('/v1/case', { id: _case })
    .then((res) => {
      if (res.data?.length === 0) {
        window.$message?.error(
          '无法获取本测试用例详细数据，请联系管理员进行处理'
        );
      } else {
        [caseDetail.value] = res.data;
      }
    })
    .catch(() => {
      window.$message?.error('无法获取本测试用例详细数据，请检查网络连接');
    });
};

const getLogsData = (_id) => {
  axios
    .get(`/v1/analyzed/${_id}/logs`)
    .then((res) => {
      logsData.value = res.data;
    })
    .catch(() => {
      window.$message?.error('无法获取对应日志数据，请检查网络连接');
    });
};

const handleSelectRecord = (record) => {
  selectedRecord.value = record;
  getCaseDetail(record.case.id);
  getLogsData(record.id);
};

const getRecords = (_case) => {
  axios
    .get('/v1/analyzed/records', { case_id: _case })
    .then((res) => {
      res.data.forEach((item) => {
        item.create_time
          ? (item.create_time = any2standard(item.create_time))
          : 0;
      });
      originRecords.value = res.data;
    })
    .catch(() => {
      window.$message?.error(
        '无法获取此测试用例的历史分析记录，请检查网络连接'
      );
    });
};

const showDrawer = (rowData) => {
  active.value = true;
  getCases(rowData.id);
  jobId.value = rowData.id;
  title.value = rowData.name;
  milestoneId.value = rowData.milestoneId;
};

const handleLogUrlRedirect = (url) => {
  window.open(url);
};

const handleNewIssueRedirect = (suite) => {
  window.open(`https://gitee.com/src-openeuler/${suite}/issues/new`);
};

const handleSelectCase = (testcase) => {
  selectedRecord.value = null;
  if (selectedCase.value === '') {
    selectedCase.value = testcase;
    document.getElementById(`case${selectedCase.value}`).style.boxShadow =
      '0 4px 20px 4px rgba(0, 0, 0, 0.4)';
  } else {
    document.getElementById(`case${selectedCase.value}`).style.boxShadow =
      '0 4px 36px 0 rgba(190, 196, 204, 0.2)';
    selectedCase.value = testcase;
    document.getElementById(`case${selectedCase.value}`).style.boxShadow =
      '0 4px 20px 4px rgba(0, 0, 0, 0.4)';
  }
  getRecords(testcase);
};

const createTimelineType = (result) => {
  if (result === 'success') {
    return 'success';
  } else if (result === 'fail') {
    return 'error';
  }
  return 'default';
};

const emitUpdateEvent = () => {
  const recordId = selectedRecord.value.id;
  axios
    .get('/v1/analyzed/records', { case_id: selectedCase.value })
    .then((res) => {
      res.data.forEach((item) => {
        item.create_time
          ? (item.create_time = any2standard(item.create_time))
          : 0;
      });
      originRecords.value = res.data;
      const [newSelectedRecord] = originRecords.value.filter(
        (item) => item.id === recordId
      );
      handleSelectRecord(newSelectedRecord);
    })
    .catch(() => {
      window.$message?.error('无法获取更新后的历史分析记录，请检查网络连接');
    });
};

const getAnalysisList = (_case, record) => {
  return [
    {
      title: '用例信息',
      name: 'caseInfo',
      rows: [
        { cols: [{ label: '用例名', value: _case.name }] },
        { cols: [{ label: '用例描述', value: _case.description }] },
      ],
    },
    {
      title: '分析记录',
      name: 'analysisRecord',
      rows: [
        { cols: [{ label: '问题类型', value: record.fail_type }] },
        { cols: [{ label: '问题描述', value: record.details, type: 'pre' }] },
        {
          cols: [{ label: 'issue地址', value: record.issue_url, type: 'html' }],
        },
        { cols: [{ label: '日志地址', value: record.log_url, type: 'html' }] },
      ],
    },
  ];
};

export default {
  active,
  title,
  records,
  selectedCase,
  selectedRecord,
  jobId,
  analyzeds,
  caseDetail,
  logsData,
  successCheck,
  failCheck,
  searchCaseValue,
  updateModalRef,
  updateFormRef,
  recordsTimeRange,
  failRecordsOnly,
  sameMilestoneOnly,
  handleLogUrlRedirect,
  handleSelectCase,
  handleSelectRecord,
  getCases,
  getRecords,
  showDrawer,
  createTimelineType,
  handleNewIssueRedirect,
  emitUpdateEvent,
  getAnalysisList,
};
