import axios from '@/axios';
import { createSuccessMsg, unkonwnErrorMsg } from '@/assets/utils/description';
function postRequest(url, data) {
  return new Promise((resolve, reject) => {
    axios
      .post(url, data)
      .then((res) => {
        if (data.webMessage !== 'manual') {
          window.$message?.success(createSuccessMsg);
        }
        resolve(res);
      })
      .catch((err) => {
        if (data.webMessage !== 'manual') {
          window.$message?.error(err.data.error_msg || unkonwnErrorMsg);
        }
        reject(err);
      });
  });
}
export function createRepo(data) {
  return postRequest('/v1/git_repo', data);
}
export function implementTemplate(data) {
  return postRequest('/v1/job/template', data);
}
export function createCaseReview (data) {
  return postRequest('/v1/case/commit', data);
}
export function getCaseReview (data) {
  return postRequest('/v1/case/commit/query', { webMessage: 'manual', ...data });
}
export function createComment (commitId,data) {
  return postRequest(`/v1/case/${commitId}/comment`, { webMessage: 'manual', ...data });
}

export function getPendingReview (data) {
  return postRequest('/v1/case/commit/status',{ webMessage: 'manual', ...data });
}
export function getCaseCommit (data) {
  return postRequest('/v1/user/case/commit', { webMessage: 'manual', ...data });
}
export function createMachineGroup(data){
  return postRequest('/v1/machine_group',data);
}
