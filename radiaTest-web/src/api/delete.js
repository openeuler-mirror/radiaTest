import { deleteSuccessMsg, unkonwnErrorMsg } from '@/assets/utils/description';
import axios from '@/axios';
function deleteRequest(url, data) {
  return new Promise((resolve, reject) => {
    axios
      .delete(url, data)
      .then((res) => {
        window.$message?.success(deleteSuccessMsg);
        resolve(res);
      })
      .catch((err) => {
        window.$notification?.error({ content: err.data.error_msg || unkonwnErrorMsg });
        reject(err);
      });
  });
}
export function deleteRepo(id) {
  return deleteRequest(`/v1/git-repo/${id}`);
}
export function deleteVm(id) {
  return deleteRequest(`/v1/vmachine/${id}/force`);
}
export function deleteCommit(id) {
  return deleteRequest(`/v1/case/commit/${id}`);
}
export function deleteComment(id) {
  return deleteRequest(`/v1/commit/comment/${id}`);
}
export function deleteMachineGroup(id) {
  return deleteRequest(`/v1/machine-group/${id}`);
}
export function deleteGroupUserRole(id, data) {
  return deleteRequest(`/v1/user-role/group/${id}`, data);
}
export function deleteOrgUserRole(id, data) {
  return deleteRequest(`/v1/user-role/org/${id}`, data);
}

export function deleteCheckListItem(id) {
  return deleteRequest(`/v1/checklist/${id}`);
}

export function deleteCheckItem(id) {
  return deleteRequest(`/v1/checkitem/${id}`);
}

export function deleteMilestoneAjax(id) {
  return deleteRequest(`/v2/milestone/${id}`);
}
