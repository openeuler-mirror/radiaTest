import axios from '@/axios';
import { lyla } from 'lyla';
import { unkonwnErrorMsg } from '@/assets/utils/description';
import config from '@/assets/config/settings';
import { storage } from '@/assets/utils/storageUtils';

function postRequest(url, data) {
  return new Promise((resolve, reject) => {
    axios
      .post(url, data)
      .then((res) => {
        resolve(res);
      })
      .catch((err) => {
        if (data?.webMessage !== 'manual') {
          window.$notification?.error({
            content: err.data.error_msg || unkonwnErrorMsg,
            duration: 5000,
            keepAliveOnHover: true
          });
        }
        reject(err);
      });
  });
}
export function createRepo(data) {
  return postRequest('/v1/git-repo', data);
}
export function implementTemplate(data) {
  return postRequest('/v1/job/template', data);
}
export function createCaseReview(data) {
  return postRequest('/v1/case/commit', data);
}
export function createComment(commitId, data) {
  return postRequest(`/v1/case/${commitId}/comment`, {
    webMessage: 'manual',
    ...data
  });
}
export function createProductMessage(productId) {
  return postRequest('/v1/qualityboard', {
    product_id: productId
  });
}
export function createMachineGroup(data) {
  return postRequest('/v1/machine-group', data);
}
export function cloneTemplate(data) {
  return postRequest('/v1/template/clone', data);
}
export function setGroupUserRole(id, data) {
  return postRequest(`/v1/user-role/group/${id}`, {
    webMessage: 'manual',
    ...data
  });
}
export function setOrgUserRole(id, data) {
  return postRequest(`/v1/user-role/org/${id}`, {
    webMessage: 'manual',
    ...data
  });
}
export function setGroupRepo(data) {
  return postRequest('/v1/git-repo', data);
}
export function setPackageListComparationDetail(qualityboardId, roundCompareeId, roundCurId, params) {
  return postRequest(
    `/v1/qualityboard/${qualityboardId}/round/${roundCompareeId}/with/${roundCurId}/pkg-compare`,
    params
  );
}

export function addCheckListItem(data) {
  return postRequest('/v1/checklist', data);
}

export function addCheckItem(data) {
  return postRequest('/v1/checkitem', data);
}

export function applyUserGroup(id) {
  return postRequest(`/v1/groups/${id}/apply`);
}

export function orgPublishRequire(orgId, data) {
  return postRequest(`/v1/requirement/org/${orgId}`, data);
}

export function groupPublishRequire(groupId, data) {
  return postRequest(`/v1/requirement/group/${groupId}`, data);
}

export function publishRequire(data) {
  return postRequest('/v1/requirement', data);
}

export function addAttachment(id, formData, onProgress) {
  return lyla.post(`https://${config.serverPath}/api/v1/requirement/${id}/attachment`, {
    withCredentials: true,
    headers: {
      Authorization: `JWT ${storage.getValue('token')}`
    },
    body: formData,
    onUploadProgress: ({ percent }) => {
      onProgress({ percent: Math.ceil(percent) });
    }
  });
}

export function addRequireProgress(id, data) {
  return postRequest(`/v1/requirement/${id}/progress`, data);
}

export function validateRequirePackage(requireId, packageId, data) {
  return postRequest(`/v1/requirement/${requireId}/package/${packageId}/validate`, data);
}

export function addRequirePackageTask(requireId, packageId, data) {
  return postRequest(`/v1/requirement/${requireId}/package/${packageId}/task`, data);
}

export function divideRequireRewards(requireId, data) {
  return postRequest(`/v1/requirement/${requireId}/reward`, data);
}

export function setHomonymousIsomerismPkgcompare(qualityboardId, roundId, params) {
  return postRequest(`/v1/qualityboard/${qualityboardId}/round/${roundId}/pkg-compare`, params);
}

export function addBaselineTemplate(data) {
  return postRequest('/v1/baseline-template', data);
}

export function addSuiteDocument(suiteId, data) {
  return postRequest(`/v1/suite/${suiteId}/document`, data);
}

export function addBaseNode(baselineTemplateId, data) {
  return postRequest(`/v1/baseline-template/${baselineTemplateId}/base-node`, data);
}

export function inheritBaselineTemplate(inheriterId, inheriteeId) {
  return postRequest(`/v1/baseline-template/${inheriterId}/inherit/${inheriteeId}`);
}

export function addBaseline(data) {
  return postRequest('/v1/baseline', data);
}

export function casenodeApplyTemplate(caseNodeId, baselineTemplateId) {
  return postRequest(`/v1/case-node/${caseNodeId}/apply/baseline-template/${baselineTemplateId}`);
}

export function createManualJob(data) {
  return postRequest('/v1/manual-job', data);
}

export function submitManualJob(jobId) {
  return postRequest(`/v1/manual-job/${jobId}/submit`);
}

// 录入特性
export function createProductFeature(data) {
  return postRequest('/v1/feature', data);
}

// 继承特性
export function productInheritFeature(productId) {
  return postRequest(`/v1/product/${productId}/inherit-feature`);
}

// 创建策略
export function createStrategy(productFeatureId, data) {
  return postRequest(`/v1/product-feature/${productFeatureId}/strategy`, data);
}

// 创建策略模板
export function createStrategyTemplate(data) {
  return postRequest('/v1/strategy-template', data);
}

// 应用策略模板
export function applyStrategyTemplate(strategyTemplateId, productFeatureId) {
  return postRequest(`/v1/strategy-template/${strategyTemplateId}/apply/product-feature/${productFeatureId}`);
}

// 关联继承特性
export function relateProductFeature(productId, data) {
  return postRequest(`/v1/product/${productId}/relate`, data);
}

// 暂存测试策略
export function strategyCommitStage(strategyId, data) {
  return postRequest(`/v1/strategy/${strategyId}/strategy-commit/stage`, data);
}

// 提交测试策略
export function strategySubmmit(strategyId, data) {
  return postRequest(`/v1/strategy/${strategyId}/submmit`, data);
}

// 创建issue
export function createIssues(data) {
  return postRequest('/v1/issues', data);
}

// 为用例集目录创建新测试套节点
export function createSuites(caseNodeId, data) {
  return postRequest(`/v1/case-node/${caseNodeId}/suites`, data);
}

// 新增每日构建
export function createDailyBuild(data) {
  return postRequest('/v1/qualityboard/daily-build', data);
}

// 新增每日构建对比
export function createDailyBuildCompare(roundId, data) {
  return postRequest(`/v1/qualityboard/daily-build/with/round/${roundId}/pkg-compare`, data);
}

// 测试执行创建模板
export function createTemplate(data) {
  return postRequest('/v1/template', data);
}
