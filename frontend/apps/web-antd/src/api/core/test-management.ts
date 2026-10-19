/*
 * Copyright (c) 2026 Huawei Technologies Co., Ltd. All rights reserved.
 * This project is licensed under the Mulan PSL v2.
 * You can use it according to the terms and conditions of the Mulan PSL v2.
 * http://license.coscl.org.cn/MulanPSL2
 */

import type { PageParams, PaginatedResponse } from './pagination';
import type { TaskEventRecord } from './task-events';

import { requestClient } from '#/api/request';

export type TestEnvType = 'physical' | 'unknown' | 'vm';
export type TestJobStatus =
  | 'error'
  | 'failed'
  | 'pending'
  | 'preparing'
  | 'running'
  | 'succeeded';
export type TestEnvSetStatus =
  | 'creating_vms'
  | 'destroyed'
  | 'destroying'
  | 'error'
  | 'failed'
  | 'not_executed'
  | 'pending'
  | 'running'
  | 'succeeded';
export type TestEnvNodeStatus =
  | 'creating'
  | 'destroyed'
  | 'error'
  | 'not_executed'
  | 'pending'
  | 'ready';
export type TestCaseRunStatus =
  | 'error'
  | 'failed'
  | 'not_executed'
  | 'passed'
  | 'pending'
  | 'running'
  | 'timeout';

export interface MugenCaseRecord {
  add_disk_num: number;
  add_nic_num: number;
  case_name: string;
  commit_sha: string;
  env_type: TestEnvType;
  id: string;
  node_num: number;
  suite_name: string;
  synced_at: string;
}

export interface TestCaseSelectionPayload {
  case_names?: null | string[];
  suite_name: string;
}

export interface TestJobCreatePayload {
  arch: string;
  cases: TestCaseSelectionPayload[];
  dist: string;
  env_set_num: number;
  env_type: 'vm';
  framework: 'mugen';
  image_round: string;
  keep_failed_env: boolean;
  name: string;
  os_version: string;
  post_env_script?: null | string;
  pre_env_script?: null | string;
}

export interface TestEnvNodeRecord {
  created_at: string;
  id: string;
  node_index: number;
  primary_ip: null | string;
  resource_id: null | string;
  role: string;
  status: TestEnvNodeStatus;
  updated_at: string;
  vm_request_id: null | string;
}

export interface TestCaseRunRecord {
  case_name: string;
  completed_at: null | string;
  created_at: string;
  env_set_id: string;
  exit_code: null | number;
  id: string;
  started_at: null | string;
  status: TestCaseRunStatus;
  stderr_summary: null | string;
  stdout_summary: null | string;
  suite_name: string;
  updated_at: string;
}

export interface TestEnvSetRecord {
  add_disk_num: number;
  add_nic_num: number;
  case_runs: TestCaseRunRecord[];
  created_at: string;
  id: string;
  node_num: number;
  nodes: TestEnvNodeRecord[];
  set_index: number;
  status: TestEnvSetStatus;
  updated_at: string;
}

export interface TestJobRecord {
  arch: string;
  completed_at: null | string;
  created_at: string;
  creator_user_id: string;
  creator_username: null | string;
  dist: string;
  env_set_num: number;
  env_type: 'vm';
  error_code: null | string;
  error_message: null | string;
  framework: 'mugen';
  id: number;
  image_round: string;
  keep_failed_env: boolean;
  mugen_commit_sha: string;
  name: string;
  os_version: string;
  post_env_script: null | string;
  pre_env_script: null | string;
  status: TestJobStatus;
  task_id: null | string;
  updated_at: string;
}

export interface TestJobDetailRecord extends TestJobRecord {
  case_runs: TestCaseRunRecord[];
  env_sets: TestEnvSetRecord[];
}

export interface TestCaseListParams extends PageParams {
  case?: string;
  env_type?: TestEnvType;
  suite?: string;
}

export interface TestJobTemplateRecord {
  arch: string;
  can_manage: boolean;
  case_count: number;
  cases: TestCaseSelectionPayload[];
  created_at: string;
  creator_user_id: string;
  creator_username: null | string;
  dist: string;
  env_set_num: number;
  env_type: 'vm';
  framework: 'mugen';
  id: number;
  image_round: string;
  is_available: boolean;
  keep_failed_env: boolean;
  name: string;
  os_version: string;
  post_env_script: null | string;
  pre_env_script: null | string;
  suite_count: number;
  unavailable_reason: null | string;
  updated_at: string;
}

export type TestJobTemplatePayload = TestJobCreatePayload;

function idempotencyHeaders(key: string) {
  return { headers: { 'Idempotency-Key': key } };
}

export async function getTestCasesApi(params?: TestCaseListParams) {
  return requestClient.get<PaginatedResponse<MugenCaseRecord>>('/test-cases', {
    params,
  });
}

export async function getAllTestCasesApi(
  params: Omit<TestCaseListParams, 'page'> = {},
) {
  const first = await getTestCasesApi({ ...params, page: 1 });
  const items = [...first.items];
  const pageCount = Math.ceil(first.total / first.page_size);
  for (let page = 2; page <= pageCount; page += 1) {
    const response = await getTestCasesApi({ ...params, page });
    items.push(...response.items);
  }
  return items;
}

export async function syncTestCasesApi() {
  return requestClient.post<{ status: string; task_id: string }>(
    '/test-cases/sync',
  );
}

export async function getTestCaseSyncEventsApi() {
  return requestClient.get<TaskEventRecord[]>('/test-cases/sync/events');
}

export async function createTestJobApi(
  payload: TestJobCreatePayload,
  idempotencyKey: string,
) {
  return requestClient.post<TestJobDetailRecord>(
    '/test-jobs',
    payload,
    idempotencyHeaders(idempotencyKey),
  );
}

export async function getTestJobsApi(showAll: boolean, page = 1) {
  return requestClient.get<PaginatedResponse<TestJobRecord>>('/test-jobs', {
    params: { all: showAll, page },
  });
}

export async function getTestJobApi(jobId: number) {
  return requestClient.get<TestJobDetailRecord>(`/test-jobs/${jobId}`);
}

export async function getTestJobEventsApi(jobId: number) {
  return requestClient.get<TaskEventRecord[]>(`/test-jobs/${jobId}/events`);
}

export async function getTestJobTemplatesApi(page = 1) {
  return requestClient.get<PaginatedResponse<TestJobTemplateRecord>>(
    '/test-job-templates',
    { params: { page } },
  );
}

export async function getTestJobTemplateApi(templateId: number) {
  return requestClient.get<TestJobTemplateRecord>(
    `/test-job-templates/${templateId}`,
  );
}

export async function createTestJobTemplateApi(
  payload: TestJobTemplatePayload,
) {
  return requestClient.post<TestJobTemplateRecord>(
    '/test-job-templates',
    payload,
  );
}

export async function updateTestJobTemplateApi(
  templateId: number,
  payload: Partial<TestJobTemplatePayload>,
) {
  return requestClient.request<TestJobTemplateRecord>(
    `/test-job-templates/${templateId}`,
    { data: payload, method: 'PATCH' },
  );
}

export async function deleteTestJobTemplateApi(templateId: number) {
  return requestClient.delete(`/test-job-templates/${templateId}`);
}
