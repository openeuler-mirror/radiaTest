import { ref } from 'vue';
import { getCommitHistory, getCaseReviewDetails } from '@/api/get';
import { formatTime } from '@/assets/utils/dateFormatUtils';
import router from '@/router';
const timeRange = ref([new Date('2010-01-01'),Date.now()]);
const searchTitle = ref('');
const versionList = ref([]);
const showDetails = ref(false);
const detailsList = ref([
  {
    title: '用例详情',
    name: 'caseDetails',
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
]);
const activeId = ref();
function getData () {
  getCommitHistory(
    window.atob(router.currentRoute.value.params.taskid), 
    {
      title: searchTitle.value,
      start_time: formatTime(timeRange.value[0],'yyyy-MM-dd hh:mm:ss'),
      end_time: formatTime(timeRange.value[1],'yyyy-MM-dd hh:mm:ss'),
    }
  ).then(res => {
    versionList.value = res.data;
  });
}
function setDataList (info) {
  detailsList.value = [
    {
      title: '用例详情',
      name: 'caseDetails',
      rows: [
        { cols: [{ label: '机器类型', value: info.machine_type }] },
        { cols: [{ label: '机器数量', value: info.machine_num }] },
        { cols: [{ label: '描述', value: info.case_description, type: 'pre' }] },
        { cols: [{ label: '预置条件', value: info.preset, type: 'pre' }] },
        { cols: [{ label: '测试步骤', value: info.steps, type: 'pre' }] },
        { cols: [{ label: '预期结果', value: info.expectation, type: 'pre' }] },
        { cols: [{ label: '备注', value: info.remark, type: 'pre' }] },
      ],
    },
  ];
}
function handleSelectCase (id) {
  activeId.value = id;
  getCaseReviewDetails(id).then(res => {
    showDetails.value = true;
    setDataList(res.data);
  });
}

export {
  showDetails,
  activeId,
  versionList,
  timeRange,
  searchTitle,
  detailsList,
  getData,
  handleSelectCase
};
