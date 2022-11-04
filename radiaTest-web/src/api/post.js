import axios from '@/axios';
import { unkonwnErrorMsg } from '@/assets/utils/description';

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
export function setPackageListComparationDetail(qualityboardId, milestonePreId, milestoneCurId) {
  return postRequest(
    `/v1/qualityboard/${qualityboardId}/milestone/${milestonePreId}/with/${milestoneCurId}/pkg-compare`
  );
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
