import type { PaginatedResponse } from './pagination';
import type { ResourceRecord } from './resources';
import type { TaskEventRecord } from './task-events';

import { requestClient } from '#/api/request';

export interface VMImageRecord {
  arch: string;
  dist: string;
  image_round: string;
  os_version: string;
  url: string;
}

export interface VMISORecord {
  sha256: string;
  size_bytes: number;
  url: string;
}

export interface VMRequestPayload {
  arch: string;
  data_disk_count: number;
  dist: string;
  expected_ends_at?: null | string;
  extra_nic_num: number;
  image_round: string;
  image_url?: null | string;
  install_type?: 'auto' | 'manual';
  kernel_version?: null | string;
  kernel_variant?: null | string;
  kernel_rpm_url?: null | string;
  memory_mb: number;
  os_version: string;
  purpose: string;
  vcpu_count: number;
}

export interface VMRequestRecord {
  arch: string;
  cancelled_at: null | string;
  completed_at: null | string;
  created_at: string;
  data_disk_count: number;
  data_disk_size_gb: number;
  dist: string;
  error_code: null | string;
  error_message: null | string;
  expected_ends_at: null | string;
  extra_nic_num: number;
  host_attempts: Record<string, unknown>[];
  host_resource_id: null | string;
  id: string;
  image_round: string;
  image_url: string;
  install_type: 'auto' | 'manual';
  kernel_version: null | string;
  memory_mb: number;
  os_version: string;
  purpose: string;
  requester_user_id: string;
  requester_username: null | string;
  resource_id: null | string;
  status: 'cancelled' | 'creating' | 'failed' | 'pending' | 'succeeded';
  updated_at: string;
  vcpu_count: number;
}

export interface VMReleasePayload {
  reason?: null | string;
}

export type VMPowerAction = 'reboot' | 'shutdown' | 'start';

export interface VMPowerPayload {
  action: VMPowerAction;
}

export interface VMPowerRecord {
  power_state: string;
  resource_id: string;
  vm_name: null | string;
}

export interface VMConsoleRecord {
  password: null | string;
  port: null | number;
  resource_id: string;
  url: string;
  vm_name: null | string;
  websocket_port: number;
}

function idempotencyHeaders(key: string) {
  return {
    headers: {
      'Idempotency-Key': key,
    },
  };
}

export async function getVMImagesApi(dist?: string) {
  return requestClient.get<VMImageRecord[]>('/vm-images', {
    params: dist ? { dist } : undefined,
  });
}

export interface KernelVariantRecord {
  kernel_version_prefix: string;
  variant: string;
}

export async function getKernelVariantsApi(params: {
  arch: string;
  image_round: string;
  os_version: string;
}) {
  return requestClient.get<KernelVariantRecord[]>(
    '/vm-images/kernel-variants',
    { params },
  );
}

export async function uploadVMISOApi(
  file: File,
  options: {
    onProgress?: (percent: number) => void;
    signal?: AbortSignal;
  } = {},
) {
  return requestClient.post<VMISORecord>('/vm-isos', file, {
    headers: { 'Content-Type': 'application/octet-stream' },
    onUploadProgress: ({ loaded, total }) => {
      const size = total ?? file.size;
      if (size > 0) {
        options.onProgress?.(Math.min(100, Math.round((loaded / size) * 100)));
      }
    },
    params: { filename: file.name },
    signal: options.signal,
    timeout: 0,
  });
}

export async function createVMRequestApi(
  payload: VMRequestPayload,
  idempotencyKey: string,
) {
  return requestClient.post<VMRequestRecord>(
    '/vm-requests',
    payload,
    idempotencyHeaders(idempotencyKey),
  );
}

export async function createVMBatchApi(
  payload: VMRequestPayload & { specs: { arch: string; count: number }[] },
  idempotencyKey: string,
) {
  return requestClient.post<VMRequestRecord[]>(
    '/vm-requests/batch',
    payload,
    idempotencyHeaders(idempotencyKey),
  );
}

export async function getVMRequestsApi(showAll: boolean, page = 1) {
  return requestClient.get<PaginatedResponse<VMRequestRecord>>('/vm-requests', {
    params: { all: showAll, page },
  });
}

export async function cancelVMRequestApi(requestId: string) {
  return requestClient.post<VMRequestRecord>(
    `/vm-requests/${requestId}/cancel`,
  );
}

export async function getVMRequestEventsApi(requestId: string) {
  return requestClient.get<TaskEventRecord[]>(
    `/vm-requests/${requestId}/events`,
  );
}

export async function getVMsApi(showAll: boolean, page = 1, search?: string) {
  return requestClient.get<PaginatedResponse<ResourceRecord>>('/vms', {
    params: { all: showAll, page, search: search || undefined },
  });
}

export async function getVMEventsApi(resourceId: string) {
  return requestClient.get<TaskEventRecord[]>(`/vms/${resourceId}/events`);
}

export async function getVMConsoleApi(resourceId: string) {
  return requestClient.get<VMConsoleRecord>(`/vms/${resourceId}/console`);
}

export async function getVMPowerApi(resourceId: string) {
  return requestClient.get<VMPowerRecord>(`/vms/${resourceId}/power`);
}

export async function operateVMPowerApi(
  resourceId: string,
  payload: VMPowerPayload,
  idempotencyKey: string,
) {
  return requestClient.post<VMPowerRecord>(
    `/vms/${resourceId}/power`,
    payload,
    idempotencyHeaders(idempotencyKey),
  );
}

export async function refreshVMIpApi(resourceId: string) {
  return requestClient.post<ResourceRecord>(`/vms/${resourceId}/refresh-ip`);
}

export async function releaseVMApi(
  resourceId: string,
  payload: VMReleasePayload,
  idempotencyKey: string,
) {
  return requestClient.post<{ resource_id: string; status: 'queued' }>(
    `/vms/${resourceId}/release`,
    payload,
    idempotencyHeaders(idempotencyKey),
  );
}

export async function batchReleaseVMApi(
  resourceIds: string[],
  payload: VMReleasePayload,
  idempotencyKey: string,
) {
  return requestClient.post<{ destroyed: string[]; failed: string[] }>(
    '/vms/batch-release',
    { resource_ids: resourceIds, reason: payload.reason ?? null },
    idempotencyHeaders(idempotencyKey),
  );
}
