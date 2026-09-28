import type { PageParams, PaginatedResponse } from './pagination';
import type { UserRole } from './user';

import { useAppConfig } from '@vben/hooks';
import { useAccessStore } from '@vben/stores';

import { requestClient } from '#/api/request';

export type ResourceMatchMode = 'and' | 'or';

export interface ResourceListParams extends PageParams {
  arch?: string;
  bmc_ip?: string;
  cpu_model?: string;
  current_lease_purpose?: string;
  current_lease_username?: string;
  kernel_version?: string;
  mac_address?: string;
  management_status?: string;
  match?: ResourceMatchMode;
  name?: string;
  occupancy_status?: string;
  os_version?: string;
  primary_ip?: string;
  resource_code?: string;
  resource_type?: string;
  usage_scenario?: string;
}

export interface ResourceRecord {
  arch: null | string;
  bmc_ip: null | string;
  bmc_username: null | string;
  board_sn: null | string;
  connectivity_status: 'reachable' | 'unknown' | 'unreachable';
  cpu_count: null | number;
  cpu_model: null | string;
  current_lease_expected_ends_at: null | string;
  current_lease_id: null | string;
  current_lease_purpose: null | string;
  current_lease_user_id: null | string;
  current_lease_user_role: null | UserRole;
  current_lease_username: null | string;
  current_test_job_id: null | number;
  device_distribution: null | string;
  device_location: null | string;
  disk_gb: null | number;
  extra: Record<string, unknown>;
  has_bmc_password: boolean;
  has_ssh_password: boolean;
  hdd_count: null | number;
  hdd_spec: null | string;
  host_resource_id: null | string;
  host_primary_ip: null | string;
  id: string;
  is_critical: boolean;
  kernel_version: null | string;
  mac_address: null | string;
  management_status: 'active' | 'disabled' | 'maintenance';
  memory_count: null | number;
  memory_mb: null | number;
  memory_spec: null | string;
  name: null | string;
  occupancy_status: 'expired' | 'idle' | 'occupied';
  os_version: null | string;
  primary_ip: null | string;
  resource_code: string;
  resource_type: 'PHYSICAL' | 'VIRTUAL';
  ssd_card_count: null | number;
  ssd_card_spec: null | string;
  ssd_count: null | number;
  ssd_spec: null | string;
  ssh_username: string;
  tags: string[];
  test_status: 'idle' | 'testing';
  usage_scenario: null | string;
  vcpu_count: null | number;
  data_disk_count: null | number;
  data_disk_paths: string[];
  data_disk_size_gb: null | number;
  system_disk_path: null | string;
  vm_name: null | string;
  vnc_port: null | number;
  vnc_websocket_port: null | number;
}

export interface LeaseCreatePayload {
  expected_ends_at?: null | string;
  purpose: string;
}

export interface LeaseReleasePayload {
  reason?: null | string;
}

export interface LeaseExtendPayload {
  expected_ends_at: string;
}

export interface LeaseRecord {
  expected_ends_at: null | string;
  id: string;
  purpose: string;
  released_at: null | string;
  released_by_user_id: null | string;
  release_reason: null | string;
  resource_id: string;
  starts_at: string;
  user_id: string;
  username: null | string;
}

export interface ResourceCredentialRecord {
  bmc_password: null | string;
  bmc_username: null | string;
  ssh_password: null | string;
  ssh_username: string;
}

export interface ResourceUpdatePayload {
  arch?: null | string;
  bmc_password?: string;
  bmc_ip?: null | string;
  bmc_username?: null | string;
  board_sn?: null | string;
  connectivity_status?: ResourceRecord['connectivity_status'];
  cpu_count?: null | number;
  cpu_model?: null | string;
  device_distribution?: null | string;
  device_location?: null | string;
  extra?: Record<string, unknown>;
  hdd_count?: null | number;
  hdd_spec?: null | string;
  is_critical?: boolean;
  kernel_version?: null | string;
  mac_address?: null | string;
  management_status?: ResourceRecord['management_status'];
  memory_count?: null | number;
  memory_spec?: null | string;
  name?: null | string;
  os_version?: null | string;
  primary_ip?: null | string;
  ssh_password?: string;
  ssh_username?: string;
  ssd_card_count?: null | number;
  ssd_card_spec?: null | string;
  ssd_count?: null | number;
  ssd_spec?: null | string;
  tags?: string[];
  usage_scenario?: null | string;
}

export interface ResourceCreatePayload extends ResourceUpdatePayload {
  bmc_ip: string;
  bmc_password: string;
  bmc_username: string;
  primary_ip: string;
  resource_code: string;
  resource_type: 'PHYSICAL';
  ssh_password: string;
  ssh_username: string;
}

export interface ResourceImportPayload {
  content: string;
  dry_run?: boolean;
  filename?: null | string;
}

export interface ResourceImportRowResult {
  errors: string[];
  primary_ip: null | string;
  resource_code: null | string;
  row_number: number;
  status: 'created' | 'error' | 'validated';
}

export interface ResourceImportResult {
  dry_run: boolean;
  error_count: number;
  rows: ResourceImportRowResult[];
  success_count: number;
  total_rows: number;
}

export type LeaseImportPayload = ResourceImportPayload;
export type LeaseImportRowResult = ResourceImportRowResult;
export type LeaseImportResult = ResourceImportResult;

function idempotencyHeaders(key: string) {
  return {
    headers: {
      'Idempotency-Key': key,
    },
  };
}

export async function getResourcesApi(params: ResourceListParams) {
  return requestClient.get<PaginatedResponse<ResourceRecord>>('/resources', {
    params,
  });
}

export async function getResourceApi(resourceId: string) {
  return requestClient.get<ResourceRecord>(`/resources/${resourceId}`);
}

function appendDefinedParam(
  params: URLSearchParams,
  key: string,
  value: unknown,
) {
  if (value === undefined || value === null || value === '') {
    return;
  }
  params.set(key, String(value));
}

export async function exportResourcesCsvApi(params: ResourceListParams) {
  const { apiURL } = useAppConfig(import.meta.env, import.meta.env.PROD);
  const accessStore = useAccessStore();
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    appendDefinedParam(searchParams, key, value);
  }
  const response = await fetch(
    `${apiURL}/resources/exports?${searchParams.toString()}`,
    {
      headers: {
        Authorization: accessStore.accessToken
          ? `Bearer ${accessStore.accessToken}`
          : '',
      },
    },
  );
  if (!response.ok) {
    throw new Error('资源导出失败');
  }
  return response.blob();
}

export async function occupyResourceApi(
  resourceId: string,
  payload: LeaseCreatePayload,
  idempotencyKey: string,
) {
  return requestClient.post<LeaseRecord>(
    `/resources/${resourceId}/leases`,
    payload,
    idempotencyHeaders(idempotencyKey),
  );
}

export async function releaseLeaseApi(
  leaseId: string,
  payload: LeaseReleasePayload,
  idempotencyKey: string,
) {
  return requestClient.post<LeaseRecord>(
    `/leases/${leaseId}/release`,
    payload,
    idempotencyHeaders(idempotencyKey),
  );
}

export async function extendLeaseApi(
  leaseId: string,
  payload: LeaseExtendPayload,
  idempotencyKey: string,
) {
  return requestClient.post<LeaseRecord>(
    `/leases/${leaseId}/extend`,
    payload,
    idempotencyHeaders(idempotencyKey),
  );
}

export async function forceReleaseLeaseApi(
  leaseId: string,
  payload: LeaseReleasePayload,
  idempotencyKey: string,
) {
  return requestClient.post<LeaseRecord>(
    `/leases/${leaseId}/force-release`,
    payload,
    idempotencyHeaders(idempotencyKey),
  );
}

export async function getResourceCredentialsApi(resourceId: string) {
  return requestClient.get<ResourceCredentialRecord>(
    `/resources/${resourceId}/credentials`,
  );
}

export async function createResourceApi(payload: ResourceCreatePayload) {
  return requestClient.post<ResourceRecord>('/resources', payload);
}

export async function updateResourceApi(
  resourceId: string,
  payload: ResourceUpdatePayload,
) {
  return requestClient.request<ResourceRecord>(`/resources/${resourceId}`, {
    data: payload,
    method: 'PATCH',
  });
}

export async function importResourcesCsvApi(
  payload: ResourceImportPayload,
  idempotencyKey?: string,
) {
  return requestClient.post<ResourceImportResult>(
    '/resources/imports',
    payload,
    idempotencyKey ? idempotencyHeaders(idempotencyKey) : undefined,
  );
}

export async function importLeasesCsvApi(
  payload: LeaseImportPayload,
  idempotencyKey?: string,
) {
  return requestClient.post<LeaseImportResult>(
    '/leases/imports',
    payload,
    idempotencyKey ? idempotencyHeaders(idempotencyKey) : undefined,
  );
}

export interface PhysicalInstallImage {
  arch: string;
  efi_url: null | string;
  id: string;
  iso_url: null | string;
  kernel_variant: null | string;
  os_version: string;
  repo_url: null | string;
  round: null | string;
  swap_kernel_variant: null | string;
}

export interface InstallBaseVariant {
  os_version: string;
  base_kernel_variant: string;
}

export async function listInstallImagesApi() {
  return requestClient.get<PhysicalInstallImage[]>('/resources/install-images');
}

export async function listInstallBaseVariantsApi() {
  return requestClient.get<InstallBaseVariant[]>(
    '/resources/install-image-base-variants',
  );
}

export async function updateInstallBaseVariantApi(
  osVersion: string,
  baseKernelVariant: string,
) {
  return requestClient.put<InstallBaseVariant>(
    '/resources/install-image-base-variants',
    {
      os_version: osVersion,
      base_kernel_variant: baseKernelVariant,
    },
  );
}

export async function createInstallImageApi(
  payload: {
    arch: string;
    efi_url: string;
    os_version: string;
    repo_url: string;
  },
  idempotencyKey?: string,
) {
  return requestClient.post<PhysicalInstallImage>(
    '/resources/install-images',
    payload,
    idempotencyKey ? idempotencyHeaders(idempotencyKey) : undefined,
  );
}

export async function deleteInstallImageApi(id: string) {
  return requestClient.delete(`/resources/install-images/${id}`);
}

export async function installResourceApi(
  resourceId: string,
  imageId: string,
  idempotencyKey?: string,
) {
  return requestClient.post<{ status: string; task_id: string }>(
    `/resources/${resourceId}/install`,
    { image_id: imageId },
    idempotencyKey ? idempotencyHeaders(idempotencyKey) : undefined,
  );
}

export async function probeResourceApi(resourceId: string) {
  return requestClient.post<{ fields_updated: string[]; status: string }>(
    `/resources/${resourceId}/probe`,
  );
}
