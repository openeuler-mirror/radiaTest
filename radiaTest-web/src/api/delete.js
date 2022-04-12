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
        window.$message?.error(err.data.error_msg || unkonwnErrorMsg);
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
