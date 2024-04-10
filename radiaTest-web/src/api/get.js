import axios from '@/axios';
import axios2 from 'axios';
import { unkonwnErrorMsg } from '@/assets/utils/description';
import { workspace } from '@/assets/config/menu.js';
import { storage } from '@/assets/utils/storageUtils';
import router from '@/router/index';

function getRequest(url, data, config, unLoginRquest) {
  return new Promise((resolve, reject) => {
    if (!storage.getValue('token') && unLoginRquest) {
      return;
    }
    let addedOrgData = {};
    if (data && url !== '/v1/login/org/list') {
      addedOrgData = data;
      addedOrgData.org_id = storage.getLocalValue('unLoginOrgId')?.id;
    } else {
      addedOrgData.org_id = storage.getLocalValue('unLoginOrgId')?.id;
    }
    axios
      .get(url, addedOrgData, config)
      .then((res) => {
        resolve(res);
      })
      .catch((err) => {
        if (!storage.getValue('token') && !addedOrgData.org_id) {
          router.replace(`/blank?redirect=${router.currentRoute.value.fullPath}`);
          window.$notification?.error({
            content: '登录过期,请重新登录',
            duration: 5000,
            keepAliveOnHover: true
          });
          return;
        }
        if (!axios2.isCancel(err)) {
          window.$notification?.error({
            content: err?.data?.error_msg || unkonwnErrorMsg,
            duration: 5000,
            keepAliveOnHover: true
          });
        }
        reject(err);
      });
  });
}
function getRequestWithoutCatch(url, data) {
  return new Promise((resolve, reject) => {
    axios
      .get(url, data)
      .then((res) => {
        resolve(res);
      })
      .catch((err) => {
        reject(err);
      });
  });
}
export function getRepo(data) {
  return getRequest(`/v1/ws/${workspace.value}/git-repo`, data);
}
export function getSuite(data) {
  return getRequest(`/v1/ws/${workspace.value}/suite`, data);
}
export function getPm(data) {
  return getRequest('/v1/accessable-machines', {
    machine_type: 'physical',
    ...data
  });
}
export function getVm(data) {
  return getRequest('/v1/accessable-machines', {
    machine_type: 'kvm',
    ...data
  });
}

export function getTemplateInfo(id, data) {
  return getRequest(`/v1/template/${id}`, data);
}
export function getTemplateList(data) {
  return getRequest(`/v1/ws/${workspace.value}/template`, data);
}
export function getIssue(data) {
  return getRequest('/v2/gitee-issues', data);
}
export function getRoundIssue(roundId, data) {
  return getRequest(`/v1/round/${roundId}/issues`, data);
}
export function getIssueType(data) {
  return getRequest('/v1/issue-types', data);
}
export function getAllOrg(data) {
  return getRequest('/v1/login/org/list', data);
}
export function loginByCode(data) {
  return getRequest('/v1/login', data);
}
export function getGroup(data, config = null, unLoginRquest = true) {
  return getRequest('/v1/groups', data, config, unLoginRquest);
}
export function getMsgGroup(data) {
  return getRequest('/v1/msg/group', data);
}


// 需要后端适配
export function getMachineGroup(data) {
  return getRequest('/v1/ws/default/machine-group', data);
}
export function getRootCert(data) {
  return new Promise((resolve, reject) => {
    axios
      .get('/v1/ca-cert', data, { responseType: 'arraybuffer' })
      .then((res) => {
        resolve(res);
      })
      .catch((err) => {
        reject(err);
        window.$notification?.error({ content: err.data.error_msg || unkonwnErrorMsg });
      });
  });
}


export function getCaseDetail(id, data) {
  return getRequest(`/v1/case/${id}`, data);
}

export function getExtendRole(data) {
  return getRequest('/v1/role/default', data);
}
export function getMilestoneTask(milestoneId, data) {
  return getRequest(`/v1/milestone/${milestoneId}/tasks`, data);
}
export function getMilestone(productId, data) {
  return getRequest(`/v1/milestone/preciseget?product_id=${productId}`, data);
}

// 需要后端适配
export function getAllMilestone(data) {
  return getRequest('v2/ws/default/milestone', data);
}
export function getProductMessage(productId, data) {
  return getRequest(`/v1/qualityboard?product_id=${productId}`, data);
}
export function getMilestoneRate(milestoneId, data) {
  return getRequest(`/v2/milestone/${milestoneId}/issue-rate`, data);
}
export function getIssueDetails(id, data) {
  return getRequest(`/v1/gitee-issues/${id}`, data);
}
export function getAllRole(data) {
  return getRequest('/v1/role', data);
}
export function getOrgUser(id, data) {
  return getRequest(`/v1/org/${id}/users`, data);
}
export function getOrgGroup(id, data) {
  return getRequest(`/v1/org/${id}/groups`, data);
}

// 需要后端适配
export function getProduct(data) {
  return getRequest('/v1/ws/default/product', data);
}
export function getCaseNodeTask(id, data) {
  return getRequest(`/v1/case-node/${id}/task`, data);
}
export function getOrgNode(id, data) {
  return getRequest(`/v1/org/${id}/resource`, data);
}

export function getTermNode(id, data) {
  return getRequest(`/v1/group/${id}/resource`, data);
}

export function getAtOverview(id, params) {
  return getRequest(`/v1/qualityboard/${id}/at`, params);
}

export function getQualityDefend(id, params) {
  return getRequest(`/v1/qualityboard/${id}/quality-defend`, params);
}

export function getDailyBuildSingle(id) {
  return getRequest(`/v1/dailybuild/${id}`);
}

export function getDailyBuildBatch(id, params) {
  return getRequest(`/v1/qualityboard/${id}/dailybuild`, params);
}

export function getWeeklybuildData(id, params) {
  return getRequest(`/v1/qualityboard/${id}/weeklybuild-health`, params);
}

export function getWeeklybuildDetail(id) {
  return getRequest(`/v1/weeklybuild/${id}`);
}

export function getFeatureCompletionRates(id) {
  return getRequest(`/v1/qualityboard/${id}/feature-list/summary`);
}

export function getFeatureList(id, params) {
  return getRequest(`/v1/qualityboard/${id}/feature-list`, params);
}

export function getPackageListComparationSummaryAxios(qualityboardId, roundId, params) {
  return getRequestWithoutCatch(`/v1/qualityboard/${qualityboardId}/round/${roundId}/pkg-list`, params);
}

export function getPackageListComparationDetail(qualityboardId, roundCompareeId, roundCurId, params) {
  return getRequestWithoutCatch(
    `/v1/qualityboard/${qualityboardId}/round/${roundCompareeId}/with/${roundCurId}/pkg-compare`,
    params
  );
}

export function getCheckListTableRounds(data) {
  return getRequest('/v1/checklist/rounds-count', data);
}

export function getCheckListTableDataAxios(data) {
  return getRequest('/v1/checklist', data);
}

export function getMilestonesByName(data) {
  return getRequest('/v2/gitee-milestone', data);
}

export function getUserAssetRank(params) {
  return getRequest('/v1/user/rank', params);
}

export function getUserInfo(userId, params, config = null, unLoginRquest = true) {
  return getRequest(`/v1/users/${userId}`, params, config, unLoginRquest);
}

export function getRequireList(params) {
  return getRequest('/v1/requirement', params);
}

export function getRequireItem(id, params) {
  return getRequest(`/v1/requirement/${id}`, params);
}

export function getRequireProgress(id, params) {
  return getRequest(`/v1/requirement/${id}/progress`, params);
}

export function getRequirePackage(id, params) {
  return getRequest(`/v1/requirement/${id}/package`, params);
}

export function downloadAttachment(id, params) {
  return getRequest(`/v1/requirement/${id}/attachment/download`, params);
}

export function getAttachmentList(id, params) {
  return getRequest(`/v1/requirement/${id}/attachment`, params);
}

export function getRequireAttributors(id, params) {
  return getRequest(`/v1/requirement/${id}/attributor`, params);
}

// 需要后端适配
export function getMilestones(data) {
  return getRequest('/v2/ws/default/milestone', data);
}

export function getRoundIssueRate(roundId) {
  return getRequest(`/v1/round/${roundId}/issue-rate`);
}

export function getHomonymousIsomerismPkgcompare(qualityboardId, roundId, params) {
  return getRequestWithoutCatch(`/v1/qualityboard/${qualityboardId}/round/${roundId}/pkg-compare`, params);
}



export function getCaseNodeResource(id, data) {
  return getRequest(`/v1/case-node/${id}/resource`, data);
}

// 需要后端适配
export function getBaselineTemplates(data) {
  return getRequest('/v1/ws/default/baseline-template', data);
}
export function getBaselineTemplateItem(id, data) {
  return getRequest(`/v1/baseline-template/${id}`, data);
}

export function getScopedGitRepo(data) {
  return getRequest('/v1/git-repo/scoped', data);
}

// 需要后端适配
export function getFramework(data) {
  return getRequest('/v1/ws/default/framework', data);
}
export function getSuiteDocuments(suiteId, data) {
  return getRequest(`/v1/suite/${suiteId}/document`, data);
}

export function getBaseNode(baseNodeId, data) {
  return getRequest(`/v1/base-node/${baseNodeId}`, data);
}

export function getCaseSetNodes(_type, id, data) {
  return getRequest(`/v1/${_type}/${id}/caseset`, data);
}

export function getCaseNode(caseNodeId, data) {
  return getRequest(`/v1/case-node/${caseNodeId}`, data);
}

export function getGroupMilestone(groupId, data) {
  return getRequest(`/v1/group/${groupId}/milestone`, data);
}

export function getOrgMilestone(orgId, data) {
  return getRequest(`/v1/org/${orgId}/milestone`, data);
}

export function getCaseNodeRoot(caseNodeId, data) {
  return getRequest(`/v1/case-node/${caseNodeId}/get-root`, data);
}

export function getSuiteItem(suiteId) {
  return getRequest(`/v1/suite/${suiteId}`);
}



export function getChecklistResult(roundId) {
  return getRequest(`/v1/round/${roundId}/checklist-result`);
}

export function getRpmcheck(qualityBoardId) {
  return getRequest(`/v1/qualityboard/${qualityBoardId}/rpmcheck`);
}

export function getMilestoneProgress(milestoneId) {
  return getRequestWithoutCatch(`/v1/milestone/${milestoneId}/task-progress`);
}

export function getMilestoneProgressCaseNode(milestoneId, caseNode) {
  return getRequest(`/v1/milestone/${milestoneId}/task-progress/case-node/${caseNode}`);
}

// 查询round列表
export function getRoundIdList(productId) {
  return getRequest(`/v1/round?product_id=${productId}`);
}

// 查询branch列表
export function getBranchList(productId, param) {
  return getRequest(`/v1/qualityboard/${productId}/branch-list`, param);
}

// 获取特性集特性
export function getAllFeature(param) {
  return getRequest('/v1/feature', param);
}

// 查询特性
export function getProductFeature(productId, param) {
  return getRequest(`/v1/product/${productId}/feature`, param);
}

// 查询测试策略
export function getStrategy(productFeatureId) {
  return getRequest(`/v1/product-feature/${productFeatureId}/strategy`);
}

// 查询测试策略模板
export function getStrategyTemplate(param) {
  return getRequest('/v1/strategy-template', param);
}

// 多版本软件包
export function getMultiVersionPackageAxios(roundId, param) {
  return getRequest(`/v1/round/${roundId}/repeat-rpm`, param);
}

// 查询代码仓
export function getGiteeProject() {
  return getRequest('/v1/gitee-project');
}



// 查询组织游离测试套列表
export function getOrphanOrgSuites(param) {
  return getRequest('/v1/org/orphan-suites', param);
}

// 查询团队游离测试套列表
export function getOrphanGroupSuites(groupId, param) {
  return getRequest(`/v1/group/${groupId}/orphan-suites`, param);
}

// 手动触发测试代码仓解析
export function getGitRepoSync(repoId) {
  return getRequestWithoutCatch(`/v1/git-repo/${repoId}/sync`);
}

// 查询任务甘特图数据
export function getTasksGantt(data) {
  return getRequest('/v1/tasks/gantt', data);
}

// 查询甘特图里程碑
export function getGanttMilestones(data) {
  return getRequest('/v2/milestone/gantt', data);
}

// 根据测试套查测试用例
export function getCasesBySuite(data) {
  return getRequest('/v1/case-set-node', data);
}

// 查询每日构建
export function getDailyBuild(data) {
  return getRequest('/v1/qualityboard/daily-build', data);
}

// 查询每日构建比对结果
export function getDailyBuildCompare(roundId, data) {
  return getRequest(`/v1/qualityboard/daily-build/with/round/${roundId}/pkg-compare`, data);
}



// 对于组织下的测试套类型节点，根据选择的导出文件格式按测试套导出文本用例
export function exportTestsuite(orgId, caseNodeId, data) {
  return getRequest(`/v1/org/${orgId}/case-node/${caseNodeId}/export`, data);
}
// 批量同步里程碑时选择里程碑判断是否与数据库里程碑重名
export function determinMilestoneName(data) {
  return getRequest('/v2/milestone/verify-name', data);
}

// 分页查询测试套
export function getCaseSuite(data) {
  return getRequest(`/v1/ws/${workspace.value}/suite`, data);
}
// 分页查询测试用例
export function getCases(data) {
  return getRequest(`/v1/ws/${workspace.value}/case`, data);
}
// 获取手工也没叶子节点
export function getCasesNode(nodeId, data) {
  return getRequest(`/v1/case-node/${nodeId}`, data);
}


// 任务看板
export function getRelationTaskList() {
  return getRequest('/v1/tasks/family');
}
export function getTaskInfo(data, config = null, unLoginRquest = true) {
  return getRequest('/v1/user/task/info', data, config, unLoginRquest);
}
export function getMachineInfo(data) {
  return getRequest('/v1/user/machine/info', data);
}
export function getTaskFrame(data) {
  return getRequest('/v1/task/frame', data);
}
export function getTasks(data) {
  return getRequest(`/v1/ws/${workspace.value}/tasks`, data);
}
export function getTaskStatus(data) {
  return getRequest('/v1/task/status', data);
}
export function getDistributeTemplates(data) {
  return getRequest('/v1/tasks/distribute-templates', data);
}
export function getDistributeTemplateSuites(data) {
  return getRequest('/v1/tasks/distribute-templates/suites', data);
}
export function getTaskRecycleBbin(data) {
  return getRequest('/v1/tasks/recycle-bin', data);
}
export function getDetailTaskFamily(taskId, data) {
  return getRequest(`/v1/tasks/${taskId}/family`, data);
}
export function getDetailTasks(taskId, data) {
  return getRequest(`/v1/tasks/${taskId}`, data);
}
export function getDetailTaskCases(taskId, data) {
  return getRequest(`/v1/tasks/${taskId}/cases`, data);
}
export function getTaskComments(taskId, data) {
  return getRequest(`/v1/tasks/${taskId}/comment`, data);
}
export function getTaskParticipants(taskId, data) {
  return getRequest(`/v1/tasks/${taskId}/participants`, data);
}
export function getTaskReports(taskId, data) {
  return getRequest(`/v1/tasks/${taskId}/reports`, data);
}
export function getTaskCount(data) {
  return getRequest('/v1/task/count/total', data);
}
// 用例管理
export function getCaseRecycleBbin(data) {
  return getRequest('/v1/ws/default/case/recycle-bin', data);
}

// 用户中心

export function getGroupUser(groupInfoId, data) {
  return getRequest(`/v1/groups/${groupInfoId}/users`, data);
}
export function getRoleInfos(roleId, data) {
  return getRequest(`/v1/role/${roleId}`, data);
}
export function getRuleses(data) {
  return getRequest('/v1/scope', data);
}
export function getAdminOrg(data) {
  return getRequest('/v1/admin/org', data);
}
export function getAllOrgList(data) {
  return getRequest('/v1/orgs/all', data);
}

export function getResultModalData(data) {
  return getRequest('/v1/testcase/test-result', data);
}

