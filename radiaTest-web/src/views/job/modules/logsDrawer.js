import { ref, watch, computed } from 'vue';
import axios from '@/axios';
import { any2standard } from '@/assets/utils/dateFormatUtils';

const active = ref(false);
const title = ref('');
const selectedCase = ref('');
const selectedRecord = ref(null);
const jobId = ref(null);
const originAnalyzeds = ref([]);
const records = ref([]);
const logsData = ref([]);
const caseDetail = ref([]);
const successCheck = ref(true);
const failCheck = ref(true);
const searchCaseValue = ref(null);
const updateModalRef = ref(null);
const updateFormRef = ref(null);

const analyzeds = computed(() => originAnalyzeds.value.filter((item) => {
  return (
    (!searchCaseValue.value || item.case.includes(searchCaseValue.value)) &&
    ((item.result === 'success' && successCheck.value) ||
      (item.result === 'fail' && failCheck.value))
  );
}));

watch(active, () => {
  if (active.value === false) {
    originAnalyzeds.value = [];
    logsData.value = [];
    selectedCase.value = '';
    selectedRecord.value = null;
    records.value = [];
  }
});

const getCases = (id) => {
  if (active.value === true) {
    axios
      .get('/v1/analyzed', { job_id: id })
      .then((res) => {
        if (res.length === 0) {
          active.value = false;
          window.$message?.error(
            '无法获取本测试任务的分析数据，请联系管理员进行处理'
          );
        } else {
          const tmpList = [];
          res.forEach((item) => {
            if (!tmpList.includes(item.case)) {
              tmpList.push(item.case);
              originAnalyzeds.value.push(item);
            }
          });
        }
      })
      .catch(() => {
        active.value = false;
        window.$message?.error(
          '无法获取本测试任务的分析数据，请检查网络连接'
        );
      });
  }
};

const getCaseDetail = (_case) => {
  axios
    .get('/v1/case', { name: _case })
    .then((res) => {
      if (res.length === 0) {
        window.$message?.error(
          '无法获取本测试用例详细数据，请联系管理员进行处理'
        );
      } else {
        [caseDetail.value] = res;
      }
    })
    .catch(() => {
      window.$message?.error(
        '无法获取本测试用例详细数据，请检查网络连接'
      );
    });
};

const getLogsData = (_id) => {
  axios
    .get('/v1/analyzed/logs', { id: _id })
    .then((res) => {
      logsData.value = res;
    })
    .catch(() => {
      window.$message?.error(
        '无法获取对应日志数据，请检查网络连接'
      );
    });
};

const handleSelectRecord = (record) => {
  if (!selectedRecord.value) {
    selectedRecord.value = record;
    document.getElementById(selectedRecord.value.id).style.backgroundColor =
        '#f0f1f2';
  } else {
    document.getElementById(selectedRecord.value.id).style.backgroundColor =
        null;
    selectedRecord.value = record;
    document.getElementById(selectedRecord.value.id).style.backgroundColor =
    '#f0f1f2';
  }

  getCaseDetail(record.case);
  getLogsData(record.id);
};

const getRecords = (_case) => {
  axios
    .get('/v1/analyzed/records', { case: _case })
    .then((res) => {
      res.forEach((item) => {
        item.create_time 
          ? item.create_time = any2standard(item.create_time) 
          : 0;
      });
      records.value = res;
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
    document.getElementById(selectedCase.value).style.boxShadow =
        '0 4px 20px 4px rgba(0, 0, 0, 0.4)';
  } else {
    document.getElementById(selectedCase.value).style.boxShadow =
        '0 4px 36px 0 rgba(190, 196, 204, 0.2)';
    selectedCase.value = testcase;
    document.getElementById(selectedCase.value).style.boxShadow =
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
    .get('/v1/analyzed/records', { case: selectedCase.value })
    .then((res) => {
      res.forEach((item) => {
        item.create_time 
          ? item.create_time = any2standard(item.create_time) 
          : 0;
      });
      records.value = res;
      const [ newSelectedRecord ] = records.value.filter(
        item => item.id === recordId
      );
      handleSelectRecord(newSelectedRecord);
    })
    .catch(() => {
      window.$message?.error(
        '无法获取更新后的历史分析记录，请检查网络连接'
      );
    });
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
  handleLogUrlRedirect,
  handleSelectCase,
  handleSelectRecord,
  getCases,
  getRecords,
  showDrawer,
  createTimelineType,
  handleNewIssueRedirect,
  emitUpdateEvent,
};
