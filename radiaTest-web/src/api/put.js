import { modifySuccessMsg, unkonwnErrorMsg } from '@/assets/utils/description';
import axios from '@/axios';
function putRequest (url, data) {
  return new Promise((resolve, reject) => {
    axios
      .put(url, data)
      .then((res) => {
        window.$message?.success(modifySuccessMsg);
        resolve(res);
      })
      .catch((err) => {
        window.$notification?.error({ content: err.data.error_msg || unkonwnErrorMsg, duration: 2000 });
        reject(err);
      });
  });
}
export function modifyRepo (id, data) {
  return putRequest(`/v1/git-repo/${id}`, data);
}
export function modifyVmachineIp (id, data) {
  return putRequest(`/v1/vmachine/${id}/ipaddr`, data);
}
export function modifyVmachineSsh (id, data) {
  return putRequest(`/v1/vmachine/${id}/ssh`, data);
}
export function modifyDelayTime (id, data) {
  return putRequest(`/v1/vmachine/${id}/delay`, data);
}
export function modifyPmachineDelayTime (id, data) {
  return putRequest(`/v1/pmachine/${id}/delay`, data);
}
export function modifyPmachineBmc (id, data) {
  return putRequest(`/v1/pmachine/${id}/bmc`, data);
}
export function modifyPmachineSsh (id, data) {
  return putRequest(`/v1/pmachine/${id}/ssh`, data);
}
export function modifyCommitStatus (id, data) {
  return putRequest(`/v1/case/commit/${id}`, data);
}
export function modifyCommitStatusBatch (data) {
  return putRequest('/v1/case/commit/status', data);
}
export function modifyCommitInfo (id,data) {
  return putRequest(`/v1/case/commit/${id}`, data);
}
export function modifyMachineGroup(id,data){
  return putRequest(`/v1/machine-group/${id}`,data);
}
export function modifyGroupUserRole (id, data) {
  return putRequest(`/v1/user-role/group/${id}`, data);
}
export function organizationInfo (id, data) {
  return putRequest(`/v1/admin/org/${id}`, data);
}
export function milestoneNext (id, data) {
  return putRequest(`/v1/qualityboard/${id}`, data);
}
export function milestoneRollback (id) {
  return putRequest(`/v1/qualityboard/${id}/rollback`);
}
