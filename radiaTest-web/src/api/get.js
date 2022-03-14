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
export function getSuite(data){
  return getRequest('/v1/suite',data);
}
export function getPm(data){
  return getRequest('/v1/pmachine',data);
}
export function getVm(data){
  return getRequest('/v1/vmachine',data);
}
export function getChildrenJob(id,data){
  return getRequest(`/v1/job/${id}/children`,data);
}
export function getJob(data){
  return getRequest('/v1/job',data);
}
