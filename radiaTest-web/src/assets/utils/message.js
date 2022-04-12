import { unkonwnErrorMsg } from './description';
export function errorMessage (err) {
  window.$message?.error(err.data?.error_msg || err.message || unkonwnErrorMsg);
}
