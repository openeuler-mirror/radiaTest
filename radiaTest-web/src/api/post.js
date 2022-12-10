import axios from '@/axios';
import { lyla } from 'lyla';
import { unkonwnErrorMsg } from '@/assets/utils/description';
import config from '@/assets/config/settings';
import { storage } from '@/assets/utils/storageUtils';

function postRequest(url, data) {
  return new Promise((resolve, reject) => {
    axios
      .post(url, data)
      .then((res) => {
        resolve(res);
      })
      .catch((err) => {
        if (data?.webMessage !== 'manual') {
          window.$notification?.error({ content: err.data.error_msg || unkonwnErrorMsg });
        }
        reject(err);
      });
  });
}
export function createRepo(data) {
  return postRequest('/v1/git-repo', data);
}
export function implementTemplate(data) {
  return postRequest('/v1/job/template', data);
}
export function createCaseReview(data) {
  return postRequest('/v1/case/commit', data);
}
export function createComment(commitId, data) {
  return postRequest(`/v1/case/${commitId}/comment`, {
    webMessage: 'manual',
    ...data
  });
}
export function createProductMessage(productId) {
  return postRequest('/v1/qualityboard', {
    product_id: productId
  });
}
export function createMachineGroup(data) {
  return postRequest('/v1/machine-group', data);
}
export function cloneTemplate(data) {
  return postRequest('/v1/template/clone', data);
}
export function setGroupUserRole(id, data) {
  return postRequest(`/v1/user-role/group/${id}`, {
    webMessage: 'manual',
    ...data
  });
}
export function setOrgUserRole(id, data) {
  return postRequest(`/v1/user-role/org/${id}`, {
    webMessage: 'manual',
    ...data
  });
}
export function setGroupRepo(data) {
  return postRequest('/v1/git-repo', data);
}
export function setPackageListComparationDetail(qualityboardId, roundPreId, roundCurId, params) {
  return postRequest(`/v1/qualityboard/${qualityboardId}/round/${roundPreId}/with/${roundCurId}/pkg-compare`, params);
}

export function addCheckListItem(data) {
  return postRequest('/v1/checklist', data);
}

export function addCheckItem(data) {
  return postRequest('/v1/checkitem', data);
}

export function applyUserGroup(id) {
  return postRequest(`/v1/groups/${id}/apply`);
}

export function orgPublishRequire(orgId, data) {
  return postRequest(`/v1/requirement/org/${orgId}`, data);
}

export function groupPublishRequire(groupId, data) {
  return postRequest(`/v1/requirement/group/${groupId}`, data);
}

export function publishRequire(data) {
  return postRequest('/v1/requirement', data);
}

export function addAttachment(id, formData, onProgress) {
  return lyla.post(`https://${config.serverPath}/api/v1/requirement/${id}/attachment`, {
    withCredentials: true,
    headers: {
      Authorization: `JWT ${storage.getValue('token')}`
    },
    body: formData,
    onUploadProgress: ({ percent }) => {
      onProgress({ percent: Math.ceil(percent) });
    }
  });
}

export function addRequireProgress(id, data) {
  return postRequest(`/v1/requirement/${id}/progress`, data);
}

export function validateRequirePackage(requireId, packageId, data) {
  return postRequest(`/v1/requirement/${requireId}/package/${packageId}/validate`, data);
}

export function addRequirePackageTask(requireId, packageId, data) {
  return postRequest(`/v1/requirement/${requireId}/package/${packageId}/task`, data);
}

export function divideRequireRewards(requireId, data) {
  return postRequest(`/v1/requirement/${requireId}/reward`, data);
}

export function setHomonymousIsomerismPkgcompare(qualityboardId, roundId, params) {
  return postRequest(`/v1/qualityboard/${qualityboardId}/round/${roundId}/pkg-compare`, params);
}

export function addBaselineTemplate(data) {
  return postRequest('/v1/baseline-template', data);
}

export function addSuiteDocument(suiteId, data) {
  return postRequest(`/v1/suite/${suiteId}/document`, data);
}

export function addBaseNode(baselineTemplateId, data) {
  return postRequest(`/v1/baseline-template/${baselineTemplateId}/base-node`, data);
}

export function inheritBaselineTemplate(inheriterId, inheriteeId) {
  return postRequest(`/v1/baseline-template/${inheriterId}/inherit/${inheriteeId}`);
}

export function addBaseline(data) {
  return postRequest('/v1/baseline', data);
}

export function casenodeApplyTemplate(caseNodeId, baselineTemplateId) {
  return postRequest(`/v1/case-node/${caseNodeId}/apply/baseline-template/${baselineTemplateId}`);
}
