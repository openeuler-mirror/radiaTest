import axios from '@/axios';
import { unkonwnErrorMsg } from '@/assets/utils/description';
function getRequest (url, data) {
  return new Promise((resolve, reject) => {
    axios
      .get(url, data)
      .then((res) => {
        resolve(res);
      })
      .catch((err) => {
        reject(err);
        window.$notification?.error({ content: err.data.error_msg || unkonwnErrorMsg });
      });
  });
}
export function getRepo (data) {
  return getRequest('/v1/git-repo', data);
}
export function getSuite (data) {
  return getRequest('/v1/suite', data);
}
export function getPm (data) {
  return getRequest('/v1/accessable-machines', {
    machine_type: 'physical',
    ...data,
  });
}
export function getVm (data) {
  return getRequest('/v1/accessable-machines', {
    machine_type: 'kvm',
    ...data,
  });
}
export function getChildrenJob (id, data) {
  return getRequest(`/v1/job/${id}/children`, data);
}
export function getJob (data) {
  return getRequest('/v1/job', data);
}
export function getTemplateInfo (id, data) {
  return getRequest(`/v1/template/${id}`, data);
}
export function getIssue (data) {
  return getRequest('/v2/milestone/issues', data);
}
export function getIssueType (data) {
  return getRequest('/v2/milestone/issue_types', data);
}
export function getAllOrg (data) {
  return getRequest('/v1/login/org/list', data);
}
export function loginByCode (data) {
  return getRequest('/v1/login', data);
}
export function getGroup (data) {
  return getRequest('/v1/groups', data);
}
export function getCaseReview (data) {
  return getRequest('/v1/case/commit/query', data);
}
export function getMachineGroup (data) {
  return getRequest('/v1/machine-group', data);
}
export function getRootCert (data) {
  return new Promise((resolve, reject) => {
    axios
      .get('/v1/ca-cert', data, {responseType: 'arraybuffer'})
      .then((res) => {
        resolve(res);
      })
      .catch((err) => {
        reject(err);
        window.$notification?.error({ content: err.data.error_msg || unkonwnErrorMsg });
      });
  });
}
export function getCommitHistory (caseId, data) {
  return getRequest(`/v1/commit/history/${caseId}`, data);
}
export function getPmachine (data) {
  return getRequest('/v1/pmachine', data);
}
export function getPmachineBmc (pmachineId, data) {
  return getRequest(`/v1/pmachine/${pmachineId}/bmc`, data);
}
export function getPmachineSsh (pmachineId, data) {
  return getRequest(`/v1/pmachine/${pmachineId}/ssh`, data);
}
export function getVmachine (data) {
  return getRequest('/v1/vmachine', data);
}
export function getVmachineSsh (vmachineId, data) {
  return getRequest(`/v1/vmachine/${vmachineId}/ssh`, data);
}
export function getCaseReviewDetails (id, data) {
  return getRequest(`/v1/case/commit/${id}`, data);
}
export function getCaseReviewComment (id, data) {
  return getRequest(`/v1/case/${id}/comment`, data);
}
export function getCaseDetail (id, data) {
  return getRequest(`/v1/case/${id}`, data);
}
export function getCasePrecise (data) {
  return getRequest('/v1/case', data);
}
export function getExtendRole (data) {
  return getRequest('/v1/role/default', data);
}
export function getMilestoneTask (milestoneId, data) {
  return getRequest(`/v1/milestone/${milestoneId}/tasks`, data);
}
export function getMilestone (productId, data) {
  return getRequest(`/v1/milestone/preciseget?product_id=${productId}`, data);
}
export function getProductMessage (productId, data) {
  return getRequest(`/v1/qualityboard?product_id=${productId}`, data);
}
export function getMilestoneRate (milestoneId, data) {
  return getRequest(`/v2/issues/statistics/milestone/${milestoneId}?is_live=False`, data);
}
export function getMachineGroupDetails (id, data) {
  return getRequest(`/v1/machine-group/${id}`, data);
}
export function getCaseCommit (data) {
  return getRequest('/v1/user/case/commit', data);
}
export function getIssueDetails (id, data) {
  return getRequest(`/v2/milestone/issues/${id}`, data);
}
export function getPendingReview (data) {
  return getRequest('/v1/case/commit/status', data);
}
export function getAllRole (data) {
  return getRequest('/v1/role', data);
}
export function getOrgUser (id, data) {
  return getRequest(`/v1/org/${id}/users`, data);
}
export function getProduct (data) {
  return getRequest('/v1/product', data);
}
export function getCaseNodeTask (id, data) {
  return getRequest(`/v1/case-node/${id}/task`, data);
}
export function getOrgNode (id, data) {
  return getRequest(`/v1/org/${id}/resource`, data);
}

export function getTermNode (id, data) {
  return getRequest(`/v1/group/${id}/resource`, data);
}

export function getGroupRepo (id) {
  return getRequest(`/v1/git-repo/${id}`);
}
