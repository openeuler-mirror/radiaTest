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
  return deleteRequest(`/v1/git_repo/${id}`);
}
export function deleteVm(id){
  return deleteRequest(`/v1/vmachine/${id}/force`);
}
export function deleteCommit (id) {
  return deleteRequest(`/v1/case/commit/${id}`);
}
export function deleteComment (id) {
  return deleteRequest(`/v1/commit/comment/${id}`);
}
export function deleteMachineGroup(id){
  return deleteRequest(`/v1/machine_group/${id}`);
}
export function deleteGroupUserRole (id,data) {
  return deleteRequest(`/v1/user_role/group/${id}`,data);
}
export function deleteOrgUserRole (id, data) {
  return deleteRequest(`/v1/user_role/org/${id}`, data);
}
