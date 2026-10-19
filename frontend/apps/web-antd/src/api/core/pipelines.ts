/*
 * Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
 * This project is licensed under the Mulan PSL v2.
 * You can use it according to the terms and conditions of the Mulan PSL v2.
 * http://license.coscl.org.cn/MulanPSL2
 */

import { useAppConfig } from '@vben/hooks';
import { useAccessStore } from '@vben/stores';

import { requestClient } from '#/api/request';

export interface TestModuleTemplateRecord {
  case_filter: string;
  created_at?: string;
  display_name: string;
  env_set_num: number;
  env_type: string;
  id: string;
  mugen_exec_command: null | string;
  suite_name: string;
  name: string;
  node_num: number;
  pipeline_type: string;
  post_env_script: string;
  pre_env_script: string;
  rerun_env_script: string;
  result_parser: string;
  skip_packages: string[];
  test_framework: string;
  updated_at?: string;
}

export interface PipelineTypeRecord {
  created_at?: string;
  default_config: Record<string, unknown>;
  display_name: string;
  id: string;
  is_system: boolean;
  name: string;
  strategy_kind: string;
  test_framework: string;
  updated_at?: string;
}

export interface FrameworkRecord {
  display_name: string;
  name: string;
}

export interface PipelineTypeCreatePayload {
  default_config?: Record<string, unknown>;
  display_name: string;
  name: string;
  strategy_kind?: string; // defaults to 'direct_run' on backend
  test_framework?: string; // defaults to 'mugen' on backend
}

export interface LatestExecutionRecord {
  id: string;
  status: string;
  triggered_at: null | string;
}

export interface PipelineConfigRecord {
  archs: string[];
  config_data: Record<string, unknown>;
  dist: null | string;
  id: string;
  image_round: null | string;
  latest_execution?: LatestExecutionRecord | null;
  name: string;
  pipeline_type: string;
  test_framework: string;
  versions: string[];
}

export interface PipelineExecutionRecord {
  archs: string[];
  completed_at: null | string;
  config_id: string;
  config_name: string;
  id: string;
  status: string;
  triggered_at: null | string;
  triggered_by: string;
  versions: string[];
}

export interface PipelineRunRecord {
  completed_at: null | string;
  config_id: string;
  execution_id: null | string;
  id: string;
  status: string;
  triggered_at: null | string;
  triggered_by: string;
  version: string;
}

export interface PipelineRunJobRecord {
  arch: string;
  created_at?: string;
  env_type: null | string;
  id: string;
  module_template_id: string;
  pipeline_run_id: string;
  status: string;
  test_job_id: null | number;
  updated_at?: string;
}

export interface PipelineTriggerPayload {
  archs?: null | string[];
  config_id: string;
  image_round?: null | string;
  versions?: null | string[];
}

export interface PipelineRunNodeInfoRecord {
  env_set_index: null | number;
  id: string;
  node_index: null | number;
  primary_ip: null | string;
  resource_code: null | string;
  resource_id: null | string;
  role: null | string;
  run_job_id: string;
  status: null | string;
}

export interface PipelineRunJobCounts {
  error: number;
  failed: number;
  no_case: number;
  not_executed: number;
  passed: number;
  pending: number;
  running: number;
  skipped: number;
  timeout: number;
}

export interface PipelineSummaryRunJobNode {
  env_set_index: null | number;
  node_index: null | number;
  primary_ip: null | string;
  resource_code: null | string;
  role: null | string;
}

export interface PipelineSummaryRunJob {
  arch: string;
  counts: PipelineRunJobCounts;
  env_type: null | string;
  id: string;
  module_template_id: string;
  nodes: PipelineSummaryRunJobNode[];
  status: string;
}

export interface PipelineSummaryRun {
  id: string;
  jobs: PipelineSummaryRunJob[];
  status: string;
  version: string;
}

export interface PipelineExecutionSummary {
  archs: string[];
  config_id: string;
  id: string;
  runs: PipelineSummaryRun[];
  status: string;
  triggered_at: null | string;
  triggered_by: string;
  versions: string[];
}

export interface TestLogArtifactRecord {
  arch: null | string;
  artifact_name: string;
  artifact_type: string;
  content: null | string;
  id: string;
  job_id: null | string;
  module: null | string;
  pipeline_run_id: null | string;
}

export interface RunLogContent {
  content: string;
}

export interface FolderFileList {
  files: string[];
}

export interface CaseMugenLog {
  artifact_id: string;
  content: string;
  file_path: string;
  files: string[];
  run_id: string;
}

export interface PipelineTestCaseRunDetailRecord {
  detail: null | string;
  id: string;
  status: string;
  sub_test_name: string;
}

export interface PipelineTestCaseRunRecord {
  can_rerun: boolean;
  case_name: null | string;
  env_type: null | string;
  env_set_id: null | string;
  env_set_index: null | number;
  exit_code: null | number;
  id: string;
  rerun_root_case_run_id: null | string;
  rerun_source_case_run_id: null | string;
  rerun_unavailable_reason: null | string;
  status: string;
  stderr_summary: null | string;
  stdout_summary: null | string;
  suite_name: null | string;
  sub_cases: PipelineTestCaseRunDetailRecord[];
}

export interface PipelineRerunCandidateRecord extends PipelineTestCaseRunRecord {
  latest_rerun_attempt: number;
}

export interface RunJobNodeRecord {
  env_set_index: null | number;
  env_type: null | string;
  node_index: null | number;
  primary_ip: null | string;
  resource_code: null | string;
  resource_id: null | string;
  role: null | string;
}

export interface RunJobLogRecord {
  arch: null | string;
  artifact_name: string;
  artifact_type: null | string;
  content: null | string;
  id: string;
  module: null | string;
}

export interface RunJobTaskEvent {
  created_at: null | string;
  level: string;
  message: string;
  phase: string;
}

export interface RunJobRerunRecord {
  case_count: number;
  created_at: null | string;
  id: string;
  rerun_attempt: number;
  status: string;
}

export interface RunJobDetail {
  arch: string;
  can_rerun: boolean;
  case_runs: PipelineTestCaseRunRecord[];
  env_type: null | string;
  error_code: null | string;
  error_message: null | string;
  id: string;
  logs: RunJobLogRecord[];
  module_template_id: string;
  nodes: RunJobNodeRecord[];
  pipeline_run_id: string;
  rerun_attempt: number;
  rerun_candidates: PipelineRerunCandidateRecord[];
  rerun_chain: RunJobRerunRecord[];
  rerun_root_run_job_id: null | string;
  rerun_source_run_job_id: null | string;
  rerun_unavailable_reason: null | string;
  result_parser: null | string;
  status: string;
  task_events: RunJobTaskEvent[];
  test_job_id: null | number;
  update_packages: string[];
}

export interface DestroyEnvsResult {
  failed: string[];
  destroyed: string[];
}

const KNOWN_VERSIONS = [
  'openEuler-20.03-LTS-SP4',
  'openEuler-22.03-LTS-SP3',
  'openEuler-22.03-LTS-SP4',
  'openEuler-24.03-LTS-SP1',
  'openEuler-24.03-LTS-SP2',
  'openEuler-24.03-LTS-SP3',
  'openEuler-24.03-LTS-SP4',
  'openEuler-24.03-LTS-SP4-64k',
];

export function getKnownVersions() {
  return KNOWN_VERSIONS;
}

export async function getModuleTemplatesApi(params?: {
  pipeline_type?: string;
}) {
  const query = params?.pipeline_type
    ? `?pipeline_type=${encodeURIComponent(params.pipeline_type)}`
    : '';
  return requestClient.get<TestModuleTemplateRecord[]>(
    `/pipelines/module-templates${query}`,
  );
}

export async function createModuleTemplateApi(payload: {
  case_filter: string;
  display_name: string;
  env_set_num: number;
  env_type: string;
  mugen_exec_command: null | string;
  name: string;
  node_num: number;
  pipeline_type?: string;
  post_env_script: string;
  pre_env_script: string;
  result_parser: string;
  skip_packages: string[];
  suite_name: string;
  test_framework: string;
}) {
  return requestClient.post<TestModuleTemplateRecord>(
    '/pipelines/module-templates',
    payload,
  );
}

export async function updateModuleTemplateApi(
  id: string,
  payload: Partial<TestModuleTemplateRecord>,
) {
  return requestClient.put<TestModuleTemplateRecord>(
    `/pipelines/module-templates/${id}`,
    payload,
  );
}

export async function getPipelineConfigsApi() {
  return requestClient.get<PipelineConfigRecord[]>('/pipelines/configs');
}

export async function getMugenSuitesApi() {
  return requestClient.get<string[]>('/pipelines/mugen-suites');
}

export async function getPipelineTypesApi() {
  return requestClient.get<PipelineTypeRecord[]>('/pipelines/types');
}

export async function createPipelineTypeApi(
  payload: PipelineTypeCreatePayload,
) {
  return requestClient.post<PipelineTypeRecord>('/pipelines/types', payload);
}

export async function deletePipelineTypeApi(id: string) {
  return requestClient.delete(`/pipelines/types/${id}`);
}

export async function getPipelineFrameworksApi() {
  return requestClient.get<FrameworkRecord[]>('/pipelines/frameworks');
}

export async function createPipelineConfigApi(payload: {
  archs: string[];
  config_data?: Record<string, unknown>;
  dist?: null | string;
  image_round?: null | string;
  name: string;
  pipeline_type?: string;
  test_framework?: string;
  versions: string[];
}) {
  return requestClient.post<PipelineConfigRecord>(
    '/pipelines/configs',
    payload,
  );
}

export async function updatePipelineConfigApi(
  id: string,
  payload: Partial<PipelineConfigRecord>,
) {
  return requestClient.put<PipelineConfigRecord>(
    `/pipelines/configs/${id}`,
    payload,
  );
}

export async function deletePipelineConfigApi(id: string) {
  return requestClient.delete(`/pipelines/configs/${id}`);
}

export async function deletePipelineExecutionApi(id: string) {
  return requestClient.delete(`/pipelines/executions/${id}`);
}

export async function deletePipelineExecutionsByConfigApi(configId: string) {
  return requestClient.delete(`/pipelines/configs/${configId}/executions`);
}

export async function triggerPipelineApi(payload: PipelineTriggerPayload) {
  return requestClient.post<PipelineExecutionRecord>(
    '/pipelines/trigger',
    payload,
  );
}

export async function getPipelineExecutionsApi(params?: {
  config_id?: string;
  limit?: number;
}) {
  const query = params
    ? `?${new URLSearchParams(
        Object.entries(params)
          .filter(([, v]) => v !== undefined && v !== null)
          .map(([k, v]) => [k, String(v)]),
      ).toString()}`
    : '';
  return requestClient.get<PipelineExecutionRecord[]>(
    `/pipelines/executions${query}`,
  );
}

export async function getPipelineExecutionApi(id: string) {
  return requestClient.get<PipelineExecutionRecord>(
    `/pipelines/executions/${id}`,
  );
}

export async function getExecutionSummaryApi(executionId: string) {
  return requestClient.get<PipelineExecutionSummary>(
    `/pipelines/executions/${executionId}/summary`,
  );
}

export async function destroyExecutionEnvsApi(executionId: string) {
  return requestClient.post<DestroyEnvsResult>(
    `/pipelines/executions/${executionId}/destroy-envs`,
    {},
  );
}

export async function getPipelineExecutionRunsApi(executionId: string) {
  return requestClient.get<PipelineRunRecord[]>(
    `/pipelines/executions/${executionId}/runs`,
  );
}

export async function getPipelineRunsApi() {
  return requestClient.get<PipelineRunRecord[]>('/pipelines/runs');
}

export async function getPipelineRunApi(id: string) {
  return requestClient.get<PipelineRunRecord>(`/pipelines/runs/${id}`);
}

export async function getPipelineRunJobsApi(runId: string) {
  return requestClient.get<PipelineRunJobRecord[]>(
    `/pipelines/runs/${runId}/jobs`,
  );
}

export async function getRunJobNodesApi(runId: string, jobId: string) {
  return requestClient.get<PipelineRunNodeInfoRecord[]>(
    `/pipelines/runs/${runId}/jobs/${jobId}/nodes`,
  );
}

export async function cancelRunJobApi(runJobId: string) {
  return requestClient.post<{ status: string }>(
    `/pipelines/run-jobs/${runJobId}/cancel`,
  );
}

export async function listRunLogsApi(runId: string) {
  return requestClient.get<TestLogArtifactRecord[]>(
    `/pipelines/runs/${runId}/logs`,
  );
}

export async function readRunLogApi(runId: string, artifactId: string) {
  return requestClient.get<RunLogContent>(
    `/pipelines/runs/${runId}/logs/${artifactId}`,
  );
}

export async function downloadRunLogApi(
  runId: string,
  artifactId: string,
): Promise<Blob> {
  const { apiURL } = useAppConfig(import.meta.env, import.meta.env.PROD);
  const accessStore = useAccessStore();
  const response = await fetch(
    `${apiURL}/pipelines/runs/${runId}/logs/${artifactId}/download`,
    {
      headers: {
        Authorization: accessStore.accessToken
          ? `Bearer ${accessStore.accessToken}`
          : '',
      },
    },
  );
  if (!response.ok) {
    throw new Error('日志下载失败');
  }
  return response.blob();
}

export async function listFolderFilesApi(runId: string, artifactId: string) {
  return requestClient.get<FolderFileList>(
    `/pipelines/runs/${runId}/logs/${artifactId}/files`,
  );
}

export async function readFolderFileApi(
  runId: string,
  artifactId: string,
  filePath: string,
) {
  return requestClient.get<RunLogContent>(
    `/pipelines/runs/${runId}/logs/${artifactId}/files?path=${encodeURIComponent(filePath)}`,
  );
}

export async function downloadFolderFileApi(
  runId: string,
  artifactId: string,
  filePath: string,
): Promise<Blob> {
  const { apiURL } = useAppConfig(import.meta.env, import.meta.env.PROD);
  const accessStore = useAccessStore();
  const response = await fetch(
    `${apiURL}/pipelines/runs/${runId}/logs/${artifactId}/files/download?path=${encodeURIComponent(filePath)}`,
    {
      headers: {
        Authorization: accessStore.accessToken
          ? `Bearer ${accessStore.accessToken}`
          : '',
      },
    },
  );
  if (!response.ok) {
    throw new Error('日志下载失败');
  }
  return response.blob();
}

export async function getRunJobDetailApi(runJobId: string) {
  return requestClient.get<RunJobDetail>(`/pipelines/run-jobs/${runJobId}`);
}

export async function rerunRunJobCasesApi(
  runJobId: string,
  caseRunIds: string[],
) {
  return requestClient.post<PipelineRunJobRecord>(
    `/pipelines/run-jobs/${runJobId}/rerun`,
    {
      case_run_ids: caseRunIds,
    },
  );
}

export async function getCaseMugenLogApi(runJobId: string, caseRunId: string) {
  return requestClient.get<CaseMugenLog>(
    `/pipelines/run-jobs/${runJobId}/case-runs/${caseRunId}/mugen-log`,
  );
}
