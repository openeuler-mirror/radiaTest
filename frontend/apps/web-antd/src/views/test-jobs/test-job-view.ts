/*
 * Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
 * This project is licensed under the Mulan PSL v2.
 * You can use it according to the terms and conditions of the Mulan PSL v2.
 * http://license.coscl.org.cn/MulanPSL2
 */

import type {
  MugenCaseRecord,
  TestCaseSelectionPayload,
  TestJobCreatePayload,
  TestJobTemplateRecord,
} from '#/api';

export interface TestJobFormState {
  arch: string;
  dist: string;
  envSetNum: number;
  imageRound: string;
  keepFailedEnv: boolean;
  name: string;
  osVersion: string;
  postEnvScript: string;
  preEnvScript: string;
}

export interface SelectionConstraints {
  addDiskNum: number;
  addNicNum: number;
  caseCount: number;
  nodeNum: number;
}

export function uniqueOptions(values: string[]) {
  return [...new Set(values.filter(Boolean))].toSorted().map((value) => ({
    label: value,
    value,
  }));
}

export function groupCasesBySuite(cases: MugenCaseRecord[]) {
  const grouped = new Map<string, MugenCaseRecord[]>();
  for (const item of cases) {
    const suiteCases = grouped.get(item.suite_name) ?? [];
    suiteCases.push(item);
    grouped.set(item.suite_name, suiteCases);
  }
  return new Map(
    [...grouped.entries()]
      .toSorted(([left], [right]) => left.localeCompare(right))
      .map(([suite, suiteCases]) => [
        suite,
        suiteCases.toSorted((left, right) =>
          left.case_name.localeCompare(right.case_name),
        ),
      ]),
  );
}

export function buildCaseSelections(
  selectedCaseNames: Record<string, string[]>,
): TestCaseSelectionPayload[] {
  return Object.entries(selectedCaseNames)
    .filter(([, caseNames]) => caseNames.length > 0)
    .toSorted(([left], [right]) => left.localeCompare(right))
    .map(([suiteName, caseNames]) => ({
      case_names: [...new Set(caseNames)].toSorted(),
      suite_name: suiteName,
    }));
}

export function inferSelectionConstraints(
  cases: MugenCaseRecord[],
  selections: TestCaseSelectionPayload[],
): SelectionConstraints {
  const selected = new Set(
    selections.flatMap((selection) =>
      (selection.case_names ?? []).map(
        (caseName) => `${selection.suite_name}\0${caseName}`,
      ),
    ),
  );
  const result: SelectionConstraints = {
    addDiskNum: 0,
    addNicNum: 0,
    caseCount: 0,
    nodeNum: 0,
  };
  for (const item of cases) {
    if (!selected.has(`${item.suite_name}\0${item.case_name}`)) continue;
    result.addDiskNum = Math.max(result.addDiskNum, item.add_disk_num);
    result.addNicNum = Math.max(result.addNicNum, item.add_nic_num);
    result.caseCount += 1;
    result.nodeNum = Math.max(result.nodeNum, item.node_num);
  }
  return result;
}

export function isCaseSelectable(item: MugenCaseRecord) {
  return item.env_type === 'vm' && item.node_num <= 2;
}

export function findUnavailableCaseSelections(
  cases: MugenCaseRecord[],
  selections: TestCaseSelectionPayload[],
) {
  const available = new Map(
    cases.map((item) => [`${item.suite_name}\0${item.case_name}`, item]),
  );
  return selections.flatMap((selection) =>
    (selection.case_names ?? [])
      .filter((caseName) => {
        const item = available.get(`${selection.suite_name}\0${caseName}`);
        return !item || !isCaseSelectable(item);
      })
      .map((caseName) => `${selection.suite_name}/${caseName}`),
  );
}

export function isValidTestJobTemplateName(value: string) {
  return /^[A-Za-z0-9._-]{1,64}$/.test(value);
}

export function buildTemplateJobName(templateName: string, value: Date) {
  const part = (number: number) => String(number).padStart(2, '0');
  const timestamp = `${value.getFullYear()}${part(value.getMonth() + 1)}${part(value.getDate())}-${part(value.getHours())}${part(value.getMinutes())}${part(value.getSeconds())}`;
  return `${templateName}-${timestamp}`;
}

export function validateTestJobForm(
  form: TestJobFormState,
  selections: TestCaseSelectionPayload[],
) {
  if (!form.name.trim()) return '请输入任务名称';
  if (!form.dist || !form.osVersion || !form.imageRound || !form.arch) {
    return '请选择发行版、OS 版本、轮次和架构';
  }
  if (form.envSetNum < 1 || form.envSetNum > 20) {
    return '环境套数必须在 1 到 20 之间';
  }
  if (selections.length === 0) return '请至少选择一个测试用例';
  return null;
}

export function buildTestJobPayload(
  form: TestJobFormState,
  selections: TestCaseSelectionPayload[],
): TestJobCreatePayload {
  return {
    arch: form.arch,
    cases: selections,
    dist: form.dist,
    env_set_num: form.envSetNum,
    env_type: 'vm',
    framework: 'mugen',
    image_round: form.imageRound,
    keep_failed_env: form.keepFailedEnv,
    name: form.name.trim(),
    os_version: form.osVersion,
    post_env_script: form.postEnvScript.trim() || null,
    pre_env_script: form.preEnvScript.trim() || null,
  };
}

function normalizeTemplatePayload(payload: TestJobCreatePayload) {
  const selectedCaseNames = Object.fromEntries(
    payload.cases.map((selection) => [
      selection.suite_name,
      selection.case_names ?? [],
    ]),
  );
  return {
    ...payload,
    cases: buildCaseSelections(selectedCaseNames),
  };
}

export function buildTestJobTemplatePatch(
  template: TestJobTemplateRecord,
  payload: TestJobCreatePayload,
) {
  const current = normalizeTemplatePayload({
    arch: template.arch,
    cases: template.cases,
    dist: template.dist,
    env_set_num: template.env_set_num,
    env_type: template.env_type,
    framework: template.framework,
    image_round: template.image_round,
    keep_failed_env: template.keep_failed_env,
    name: template.name,
    os_version: template.os_version,
    post_env_script: template.post_env_script,
    pre_env_script: template.pre_env_script,
  });
  const next = normalizeTemplatePayload(payload);
  const patch: Partial<TestJobCreatePayload> = {};
  for (const key of Object.keys(next) as Array<keyof TestJobCreatePayload>) {
    if (JSON.stringify(current[key]) !== JSON.stringify(next[key])) {
      Object.assign(patch, { [key]: next[key] });
    }
  }
  return patch;
}

export function testStatusLabel(status: string) {
  const labels: Record<string, string> = {
    creating: '创建中',
    creating_vms: '创建 VM',
    destroyed: '已销毁',
    destroying: '销毁中',
    error: '异常',
    failed: '失败',
    passed: '通过',
    pending: '排队中',
    preparing: '准备中',
    ready: '就绪',
    running: '运行中',
    succeeded: '成功',
    timeout: '超时',
  };
  return labels[status] ?? status;
}

export function testStatusColor(status: string) {
  if (['passed', 'ready', 'succeeded'].includes(status)) return 'green';
  if (
    ['creating', 'creating_vms', 'pending', 'preparing', 'running'].includes(
      status,
    )
  ) {
    return 'blue';
  }
  if (['destroyed', 'destroying'].includes(status)) return 'default';
  if (status === 'timeout') return 'orange';
  return 'red';
}
