import axios from '@/axios';
import { unkonwnErrorMsg } from '@/assets/utils/description';
function postRequest (url, data) {
  return new Promise((resolve, reject) => {
    axios
      .post(url, data)
      .then((res) => {
        resolve(res);
      })
      .catch((err) => {
        if (data.webMessage !== 'manual') {
          window.$notification?.error({ content: err.data.error_msg || unkonwnErrorMsg, duration: 2000 });
        }
        reject(err);
      });
  });
}
export function createRepo (data) {
  return postRequest('/v1/git_repo', data);
}
export function implementTemplate (data) {
  return postRequest('/v1/job/template', data);
}
export function createCaseReview (data) {
  return postRequest('/v1/case/commit', data);
}
export function createComment (commitId, data) {
  return postRequest(`/v1/case/${commitId}/comment`, {
    webMessage: 'manual',
    ...data,
  });
}
export function createMachineGroup (data) {
  return postRequest('/v1/machine_group', data);
}
export function cloneTemplate (data) {
  return postRequest('/v1/templateclone', data);
}
export function setGroupUserRole (id, data) {
  return postRequest(`/v1/user_role/group/${id}`, {
    webMessage: 'manual',
    ...data,
  });
}
export function setOrgUserRole (id, data) {
  return postRequest(`/v1/user_role/org/${id}`, {
    webMessage: 'manual',
    ...data,
  });
}

