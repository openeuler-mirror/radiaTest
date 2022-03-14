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
