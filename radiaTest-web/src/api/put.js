import { modifySuccessMsg, unkonwnErrorMsg } from '@/assets/utils/description';
import axios from '@/axios';
function putRequest(url, data, msg) {
  return new Promise((resolve, reject) => {
    axios
      .put(url, data)
      .then((res) => {
        window.$message?.success(msg?.successMsg || modifySuccessMsg);
        resolve(res);
      })
      .catch((err) => {
        window.$notification?.error({ content: err.data.error_msg || unkonwnErrorMsg, duration: 2000 });
        reject(err);
      });
  });
}
export function modifyRepo(id, data) {
  return putRequest(`/v1/git-repo/${id}`, data);
}
export function modifyVmachineIp(id, data) {
  return putRequest(`/v1/vmachine/${id}/ipaddr`, data);
}
export function modifyVmachineSsh(id, data) {
  return putRequest(`/v1/vmachine/${id}/ssh`, data);
}
export function modifyDelayTime(id, data) {
  return putRequest(`/v1/vmachine/${id}/delay`, data);
}
export function modifyPmachineDelayTime(id, data) {
  return putRequest(`/v1/pmachine/${id}/delay`, data);
}
export function modifyPmachineBmc(id, data) {
  return putRequest(`/v1/pmachine/${id}/bmc`, data);
}
export function modifyPmachineSsh(id, data) {
  return putRequest(`/v1/pmachine/${id}/ssh`, data);
}
export function modifyCommitStatus(id, data) {
  return putRequest(`/v1/case/commit/${id}`, data);
}
export function modifyCommitStatusBatch(data) {
  return putRequest('/v1/case/commit/status', data);
}
export function modifyCommitInfo(id, data) {
  return putRequest(`/v1/case/commit/${id}`, data);
}
export function modifyMachineGroup(id, data) {
  return putRequest(`/v1/machine-group/${id}`, data);
}
export function modifyGroupUserRole(id, data) {
  return putRequest(`/v1/user-role/group/${id}`, data);
}
export function organizationInfo(id, data) {
  return putRequest(`/v1/admin/org/${id}`, data);
}
export function milestoneNext(id, data) {
  return putRequest(`/v1/qualityboard/${id}`, data);
}
export function milestoneRollback(id) {
  return putRequest(`/v1/qualityboard/${id}/rollback`);
}

export function updateCheckListItem(id, data) {
  return putRequest(`/v1/checklist/${id}`, data);
}

export function deselectCheckListItem(id, data) {
  return putRequest(`/v1/checklist/${id}/deselect`, data);
}

export function updateCheckItem(id, data) {
  return putRequest(`/v1/checkitem/${id}`, data);
}

export function updateSyncMilestone(id, data) {
  return putRequest(`/v2/milestone/${id}/sync`, data);
}

export function updateMilestoneState(id, data) {
  return putRequest(`/v2/milestone/${id}/state`, data);
}

export function changeAdminPassword(data) {
  return putRequest('/v1/admin/changepasswd', data);
}

export function updateProductVersion(productId, data) {
  return putRequest(`/v1/product/${productId}`, data);
}

export function updateRequireProgress(requireId, progressId, data) {
  return putRequest(`/v1/requirement/${requireId}/progress/${progressId}`, data);
}

export function updateRequirePackageValidator(requireId, packageId, userId) {
  return putRequest(`/v1/requirement/${requireId}/package/${packageId}/set-validator/${userId}`);
}

export function updateLockRequireAttachment(requireId, data) {
  return putRequest(`/v1/requirement/${requireId}/attachment/lock`, data);
}

export function personAcceptRequire(requireId, data) {
  return putRequest(`/v1/requirement/${requireId}/accept`, data);
}

export function groupAcceptRequire(requireId, groupId, data) {
  return putRequest(`/v1/requirement/${requireId}/group/${groupId}/accept`, data);
}

export function rejectRequire(requireId, data) {
  return putRequest(`/v1/requirement/${requireId}/reject`, data);
}

export function validateRequire(requireId, data) {
  return putRequest(`/v1/requirement/${requireId}/validate`, data);
}

export function roundRelateMilestonesAxios(roundId, data) {
  return putRequest(`/v1/round/${roundId}/bind-milestone`, data);
}

export function updateBaselineTemplate(id, data) {
  return putRequest(`/v1/baseline-template/${id}`, data);
}

export function updateSuiteDocument(id, data) {
  return putRequest(`/v1/suite-document/${id}`, data);
}

export function updateBaseNode(id, data) {
  return putRequest(`/v1/base-node/${id}`, data);
}

export function updateCaseNodeParent(caseNodeId, nextParentId) {
  return putRequest(`/v1/case-node/${caseNodeId}/move-to/${nextParentId}`);
}

export function updateStepLogAxios(jobId, data) {
  return putRequest(`/v1/manual-job/log/${jobId}`, data);
}

export function statisticsProduct(id) {
  return putRequest(`/v1/product/${id}/issue-rate`, {}, { successMsg: '统计成功' });
}

export function updateCompareRounds(roundId, data) {
  return putRequest(`/v1/round/${roundId}/compare-round/`, data);
}
