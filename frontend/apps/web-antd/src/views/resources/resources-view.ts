import type { ResourceListParams, ResourceMatchMode, UserRole } from '#/api';

interface ResourceLeaseContext {
  currentRole?: UserRole;
  currentUserId?: string;
}

interface ResourceLeaseOwner {
  current_lease_id: null | string;
  current_lease_user_id: null | string;
  current_lease_user_role: null | UserRole;
}

interface ResourceTestState {
  test_status: 'idle' | 'testing';
}

export type ResourceFilterKey = Exclude<
  keyof ResourceListParams,
  'match' | 'page'
>;

export interface ResourceFilterItem {
  key: ResourceFilterKey;
  label: string;
}

export const resourceFilterItems: ResourceFilterItem[] = [
  { key: 'primary_ip', label: 'OS IP' },
  { key: 'bmc_ip', label: 'BMC IP' },
  { key: 'occupancy_status', label: '占用状态' },
  { key: 'current_lease_username', label: '占用人' },
  { key: 'current_lease_purpose', label: '占用用途' },
  { key: 'usage_scenario', label: '使用场景' },
  { key: 'management_status', label: '管理状态' },
  { key: 'arch', label: '架构' },
  { key: 'cpu_model', label: 'CPU' },
  { key: 'name', label: '显示名' },
  { key: 'resource_code', label: '资源编码' },
  { key: 'mac_address', label: 'MAC' },
  { key: 'os_version', label: 'OS' },
  { key: 'kernel_version', label: '内核' },
];

export function buildResourceListParams({
  currentUsername,
  filters,
  matchMode,
  page,
  showAll,
}: {
  currentUsername?: string;
  filters: Record<ResourceFilterKey, string>;
  matchMode: ResourceMatchMode;
  page: number;
  showAll: boolean;
}): ResourceListParams {
  const params: ResourceListParams = {
    match: matchMode,
    page,
    resource_type: 'PHYSICAL',
  };

  for (const item of resourceFilterItems) {
    const value = filters[item.key].trim();
    if (value) {
      params[item.key] = value;
    }
  }
  if (!showAll && currentUsername) {
    params.current_lease_username = currentUsername;
  }

  return params;
}

export function canForceReleaseResource(
  resource: ResourceLeaseOwner,
  context: ResourceLeaseContext,
) {
  if (
    !resource.current_lease_id ||
    resource.current_lease_user_id === context.currentUserId
  ) {
    return false;
  }
  if (context.currentRole === 'ADMIN') return true;
  return (
    context.currentRole === 'TSE' && resource.current_lease_user_role === 'TE'
  );
}

export function canUseResourceDestructiveActions(resource: ResourceTestState) {
  return resource.test_status === 'idle';
}

export function resourceTestStatusLabel(
  status: ResourceTestState['test_status'],
) {
  return status === 'testing' ? '测试中' : '空闲';
}
