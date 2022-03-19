import axios from '@/axios';
import { unkonwnErrorMsg } from '@/assets/utils/description';
function getRequest(url, data) {
  return new Promise((resolve, reject) => {
    axios
      .get(url, data)
      .then((res) => {
        resolve(res);
      })
      .catch((err) => {
        reject(err);
        window.$message?.error(err.data.error_msg || unkonwnErrorMsg);
      });
  });
}
export function getRepo(data) {
  return getRequest('/v1/git_repo', data);
}
export function getSuite(data) {
  return getRequest('/v1/suite', data);
}
export function getPm(data) {
  return getRequest('/v1/pmachine', data);
}
export function getVm(data) {
  return getRequest('/v1/vmachine', data);
}
export function getChildrenJob(id, data) {
  return getRequest(`/v1/job/${id}/children`, data);
}
export function getJob(data) {
  return getRequest('/v1/job', data);
}
export function getTemplateInfo(id, data) {
  return getRequest(`/v1/template/${id}`, data);
}
export function getIssue(data) {
  return getRequest('/v2/milestone/issues', data);
}
export function getIssueType(data) {
  return getRequest('/v2/milestone/issue_types', data);
}
export function getAllOrg(data) {
  return getRequest('/v1/login/org/list', data);
}
export function loginByCode(data) {
  return getRequest('/v1/login', data);
}
