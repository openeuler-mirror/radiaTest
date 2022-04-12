import { ref } from 'vue';
import router from '@/router';
import { getCaseReviewDetails, getCaseDetail } from '@/api/get';
import { modifyCommitStatus } from '@/api/put';
import { oldContent, newContent, content } from './content';
const detailInfo = ref({});
function detailContent () {
  const oldField = ['description', 'preset', 'steps', 'expection'];
  const newField = ['case_description', 'preset', 'steps', 'expectation'];
  const descriptionField = ['描述', '预置条件', '操作步骤', '预期结果'];
  const result = [];
  oldField.forEach((item, index) => {
    result.push({
      oldContent: String(oldContent.value[item]),
      newContent: String(newContent.value[newField[index]]),
      name: descriptionField[index]
    });
  });
  return result;
}
function getDetail () {
  const commit = router.currentRoute.value.params.commitId;
  getCaseReviewDetails(commit).then(res => {
    detailInfo.value = res.data;
    newContent.value = res.data;
    getCaseDetail({
      id: res.data.case_detail_id
    }).then((response) => {
      [oldContent.value] = response.data;
      content.value = detailContent();
    });
  });
}
const statusTag = {
  pending: 'info',
  open: 'primary',
  rejected: 'error',
  accepted:'success'
};
function handleModify (status) {
  modifyCommitStatus(router.currentRoute.value.params.commitId, { status }).then(() => {
    getDetail();
  });
}
export {
  detailInfo,
  statusTag,
  getDetail,
  handleModify
};
