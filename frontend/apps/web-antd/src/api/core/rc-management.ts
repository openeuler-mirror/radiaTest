import { useAppConfig } from '@vben/hooks';
import { useAccessStore } from '@vben/stores';

import { requestClient } from '#/api/request';

/** 版本（RC 版本测试长期对象） */
export interface VersionRecord {
  id: string;
  name: string;
  version_type?: null | string;
  status: 'finished' | 'testing';
  start_time?: null | string;
  end_time?: null | string;
  remark?: null | string;
  created_by: string;
  created_at: string;
  milestone_count: number;
}

export interface VersionCreatePayload {
  name: string;
  version_type?: null | string;
  /** 创建时自动生成 round1..roundN 里程碑骨架（构建 URL 后续登记） */
  rc_round_count?: number;
  status?: string;
  start_time?: null | string;
  end_time?: null | string;
  remark?: null | string;
}

export interface VersionUpdatePayload {
  name?: string;
  version_type?: null | string;
  status?: string;
  start_time?: null | string;
  end_time?: null | string;
  remark?: null | string;
}

/** RC 里程碑（轮次） */
export interface MilestoneRecord {
  id: string;
  version_id: string;
  name: string;
  kernel_variant?: null | string;
  build_url: string;
  pxe_round_label?: null | string;
  compare_base_milestone_id?: null | string;
  compare_base_name?: null | string;
  start_time?: null | string;
  end_time?: null | string;
  created_by: string;
  created_at: string;
  has_pxe_source: boolean;
  latest_compare?: null | {
    completed_at?: null | string;
    id: string;
    status: string;
    total_changed?: null | number;
  };
}

export interface MilestoneCreatePayload {
  version_id: string;
  name: string;
  kernel_variant?: null | string;
  build_url: string;
  compare_base_milestone_id?: null | string;
  start_time?: null | string;
  end_time?: null | string;
}

export interface MilestoneUpdatePayload {
  name?: string;
  kernel_variant?: null | string;
  build_url?: string;
  compare_base_milestone_id?: null | string;
  start_time?: null | string;
  end_time?: null | string;
}

/** 比对任务实例 */
export interface CompareRecord {
  id: string;
  milestone_id: string;
  base_milestone_id: string;
  status: 'failed' | 'pending' | 'running' | 'succeeded';
  total_changed?: null | number;
  summary?: null | Record<string, Record<string, number>>;
  error_msg?: null | string;
  triggered_by: string;
  triggered_at: string;
  completed_at?: null | string;
  created_at: string;
}

/** 比对结果行（非 SAME 变更集） */
export interface CompareResultRecord {
  id: number;
  kind: 'binary' | 'isomer' | 'repeat' | 'source';
  repo_path: string;
  pkg_name: string;
  arch?: null | string;
  status: string;
  rpm_base?: null | string;
  rpm_target?: null | string;
}

export interface PageResp<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
}

export interface CompareResultsParams {
  page?: number;
  kind?: string;
  repo_path?: string;
  arch?: string;
  status?: string[];
}

/* ---------- 版本 ---------- */

export async function listVersionsApi(search?: string) {
  return requestClient.get<PageResp<VersionRecord>>('/versions', {
    params: search ? { search } : undefined,
  });
}

export async function getVersionApi(id: string) {
  return requestClient.get<VersionRecord>(`/versions/${id}`);
}

export async function createVersionApi(payload: VersionCreatePayload) {
  return requestClient.post<VersionRecord>('/versions', payload);
}

export async function updateVersionApi(
  id: string,
  payload: VersionUpdatePayload,
) {
  return requestClient.put<VersionRecord>(`/versions/${id}`, payload);
}

export async function deleteVersionApi(id: string) {
  return requestClient.delete(`/versions/${id}`);
}

/* ---------- 里程碑 ---------- */

export async function listVersionMilestonesApi(versionId: string) {
  return requestClient.get<MilestoneRecord[]>(
    `/versions/${versionId}/milestones`,
  );
}

export async function createMilestoneApi(payload: MilestoneCreatePayload) {
  return requestClient.post<MilestoneRecord>('/milestones', payload);
}

export async function updateMilestoneApi(
  id: string,
  payload: MilestoneUpdatePayload,
) {
  return requestClient.put<MilestoneRecord>(`/milestones/${id}`, payload);
}

export async function deleteMilestoneApi(id: string) {
  return requestClient.delete(`/milestones/${id}`);
}

/* ---------- 比对 ---------- */

export async function triggerCompareApi(
  milestoneId: string,
  baseMilestoneId: string,
) {
  return requestClient.post<CompareRecord>(
    `/milestones/${milestoneId}/compares`,
    { base_milestone_id: baseMilestoneId },
  );
}

export async function getCompareApi(compareId: string) {
  return requestClient.get<CompareRecord>(`/compares/${compareId}`);
}

export async function listCompareResultsApi(
  compareId: string,
  params: CompareResultsParams,
) {
  return requestClient.get<PageResp<CompareResultRecord>>(
    `/compares/${compareId}/results`,
    { params },
  );
}

/** 导出交付 zip：走 fetch 流（带 Authorization 头 + 文件名） */
export async function downloadCompareExportApi(compareId: string) {
  const { apiURL } = useAppConfig(import.meta.env, import.meta.env.PROD);
  const accessStore = useAccessStore();
  const response = await fetch(`${apiURL}/compares/${compareId}/export`, {
    headers: {
      Authorization: accessStore.accessToken
        ? `Bearer ${accessStore.accessToken}`
        : '',
    },
  });
  if (!response.ok) {
    throw new Error('比对交付物导出失败');
  }
  const disposition = response.headers.get('Content-Disposition') || '';
  const match = disposition.match(/filename="?([^";]+)"?/);
  return {
    blob: await response.blob(),
    filename: match?.[1] ?? `rc-compare-${compareId}.zip`,
  };
}
