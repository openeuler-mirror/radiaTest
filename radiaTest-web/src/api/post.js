import axios from '@/axios';
import { createSuccessMsg, unkonwnErrorMsg } from '@/assets/utils/description';
function postRequest(url, data) {
  return new Promise((resolve, reject) => {
    axios
      .post(url, data)
      .then((res) => {
        window.$message?.success(createSuccessMsg);
        resolve(res);
      })
      .catch((err) => {
        window.$message?.error(err.data.error_msg || unkonwnErrorMsg);
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
