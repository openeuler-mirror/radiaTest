import { modifySuccessMsg, unkonwnErrorMsg } from '@/assets/utils/description';
import axios from '@/axios';
function putRequest(url, data, msg, hasHeader) {
  let header = hasHeader ? {
    'Content-Type': 'multipart/form-data'
  } : null;
  return new Promise((resolve, reject) => {
    axios
      .put(url, data, { headers: header })
      .then((res) => {
        window.$message?.success(msg?.successMsg || modifySuccessMsg);
        resolve(res);
      })
      .catch((err) => {
        window.$notification?.error({
          content: err.data.error_msg || unkonwnErrorMsg,
          duration: 5000,
          keepAliveOnHover: true
        });
        reject(err);
      });
  });
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


export function organizationInfo(id, data) {
  return putRequest(`/v1/admin/org/${id}`, data, null, true);
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

// 修改弱口令
export function updateWeakPwd(id, data) {
  return putRequest(`/v1/admin/${id}/password-rule`, data);
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



export function statisticsProduct(id) {
  return putRequest(`/v1/product/${id}/issue-rate`, {}, { successMsg: '统计成功' });
}

export function updateCompareRounds(roundId, data, msg) {
  return putRequest(`/v1/round/${roundId}/compare-round`, data, msg);
}

export function updateTemplateDrawer(data, id) {
  return putRequest(`/v1/template/${id}`, data, null, true);
}

// 更新测试策略模板
export function updateStrategyTemplate(strategyTemplateId, data) {
  return putRequest(`/v1/strategy-template/${strategyTemplateId}`, data);
}



// 修改任务完成度
export function changeTaskPercentage(taskId, data) {
  return putRequest(`/v1/tasks/${taskId}/percentage`, data);
}


