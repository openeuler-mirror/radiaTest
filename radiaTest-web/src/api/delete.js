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
        window.$notification?.error({
          content: err.data.error_msg || unkonwnErrorMsg,
          duration: 5000,
          keepAliveOnHover: true
        });
        reject(err);
      });
  });
}


export function deleteCommit(id) {
  return deleteRequest(`/v1/case/commit/${id}`);
}
export function deleteComment(id) {
  return deleteRequest(`/v1/commit/comment/${id}`);
}

export function deleteGroupUserRole(id, data) {
  return deleteRequest(`/v1/user-role/group/${id}`, data);
}
export function deleteOrgUserRole(id, data) {
  return deleteRequest(`/v1/user-role/org/${id}`, data);
}


export function deleteCheckItem(id) {
  return deleteRequest(`/v1/checkitem/${id}`);
}

// 删除弱口令
export function deleteWeakPwd(id) {
  return deleteRequest(`/v1/admin/${id}/password-rule`);
}

export function deleteMilestoneAjax(id) {
  return deleteRequest(`/v2/milestone/${id}`);
}

export function deleteProductVersion(productId) {
  return deleteRequest(`/v1/product/${productId}`);
}

export function deleteRequireAttachment(id, data) {
  return deleteRequest(`/v1/requirement/${id}/attachment`, data);
}

export function deleteRequireProgress(requireId, progressId) {
  return deleteRequest(`/v1/requirement/${requireId}/progress/${progressId}`);
}

export function deleteRequire(requireId) {
  return deleteRequest(`/v1/requirement/${requireId}`);
}

export function deleteBaselineTemplate(id) {
  return deleteRequest(`/v1/baseline-template/${id}`);
}

export function deleteSuiteDocument(id) {
  return deleteRequest(`/v1/suite-document/${id}`);
}

export function deleteBaseNode(baseNodeId) {
  return deleteRequest(`/v1/base-node/${baseNodeId}`);
}

export function cleanBaselineTemplate(id) {
  return deleteRequest(`/v1/baseline-template/${id}/clean`);
}



// 删除测试策略模板
export function deleteStrategyTemplate(strategyTemplateId) {
  return deleteRequest(`/v1/strategy-template/${strategyTemplateId}`);
}

// 还原测试策略
export function deleteStrategyCommit(strategyId) {
  return deleteRequest(`/v1/strategy/${strategyId}/reduct`);
}

// 删除测试策略
export function deleteStrategy(productFeatureId, data) {
  return deleteRequest(`/v1/product-feature/${productFeatureId}/strategy`, data);
}

// 删除每日构建
export function deleteDailyBuild(data) {
  return deleteRequest('/v1/qualityboard/daily-build', data);
}

// 删除每日构建对比
export function deleteDailyBuildCompare(roundId, data) {
  return deleteRequest(`/v1/qualityboard/daily-build/with/round/${roundId}/pkg-compare`, data);
}

// 删除测试套
export function deleteSuiteAxios(suiteId, data) {
  return deleteRequest(`/v1/suite/${suiteId}`, data);
}
