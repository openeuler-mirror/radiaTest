import type {
  ResourceRecord,
  UserRole,
  VMConsoleRecord,
  VMRequestRecord,
} from '#/api';

import dayjs from 'dayjs';

export interface VMAuthContext {
  currentRole?: UserRole;
  currentUserId?: string;
}

export function uniqueOptions(values: string[]) {
  return [...new Set(values.filter(Boolean))].toSorted().map((value) => ({
    label: value,
    value,
  }));
}

export function displayValue(value: unknown) {
  return value === null || value === undefined || value === '' ? '-' : value;
}

export function findRequestedVM(
  records: ResourceRecord[],
  resourceId: null | string,
) {
  if (!resourceId) return null;
  return records.find((record) => record.id === resourceId) ?? null;
}

export function displayCredentialValue(
  hasPassword: boolean,
  canView: boolean,
  loading: boolean,
  value?: null | string,
) {
  if (!hasPassword) return '未保存';
  if (!canView) return '***';
  if (loading) return '加载中...';
  return value || '***';
}

export function statusColor(status: string) {
  if (status === 'succeeded' || status === 'active' || status === 'occupied') {
    return 'green';
  }
  if (status === 'pending' || status === 'creating' || status === 'queued') {
    return 'blue';
  }
  if (status === 'cancelled') {
    return 'default';
  }
  if (status === 'expired') {
    return 'orange';
  }
  return 'red';
}

export function statusLabel(status: string) {
  const labels: Record<string, string> = {
    cancelled: '已取消',
    creating: '创建中',
    failed: '失败',
    pending: '排队中',
    queued: '等待创建',
    succeeded: '成功',
  };
  return labels[status] ?? status;
}

export function installTypeLabel(installType: string) {
  return installType === 'manual' ? '手动' : '自动';
}

export function powerStateLabel(state?: null | string) {
  const labels: Record<string, string> = {
    crashed: '已崩溃',
    paused: '已暂停',
    running: '运行中',
    'shut off': '已关机',
  };
  return state ? (labels[state] ?? state) : '-';
}

export function powerStateColor(state?: null | string) {
  if (state === 'running') return 'green';
  if (state === 'paused') return 'orange';
  if (state === 'shut off') return 'default';
  if (state === 'crashed') return 'red';
  return 'default';
}

export function powerActionLabel(action: string) {
  const labels: Record<string, string> = {
    reboot: '重启',
    shutdown: '关机',
    start: '启动',
  };
  return labels[action] ?? action;
}

export function eventLevelColor(level: string) {
  if (level === 'error') return 'red';
  if (level === 'warning') return 'orange';
  return 'blue';
}

export function eventPhaseLabel(phase: string) {
  const labels: Record<string, string> = {
    host_command: '宿主命令',
    host_command_failed: '失败命令',
    host_command_output: '命令输出',
    host_command_stderr: '命令错误',
  };
  return labels[phase] ?? phase;
}

export function isHostCommandEvent(phase: string) {
  return [
    'host_command',
    'host_command_failed',
    'host_command_output',
    'host_command_stderr',
  ].includes(phase);
}

export function isImportantHostCommand(message: string) {
  return /(^|[\s/])(qemu(?:-[^\s/]+)?|virsh|virt-install)(\s|$)/.test(message);
}

export function shouldDisplayTaskEvent(phase: string, message = '') {
  return phase !== 'host_command' || isImportantHostCommand(message);
}

export function formatTaskEventMessage(message: string) {
  return message.replaceAll(String.raw`\n`, '\n');
}

export function formatSpec(record: ResourceRecord) {
  return `${record.vcpu_count ?? '-'}C / ${Math.round((record.memory_mb ?? 0) / 1024)}G / ${record.disk_gb ?? '-'}G`;
}

export function formatRequestSpec(record: VMRequestRecord) {
  return `${record.vcpu_count ?? '-'}C / ${Math.round((record.memory_mb ?? 0) / 1024)}G`;
}

export function formatRequestImage(record: VMRequestRecord) {
  return [record.dist, record.os_version, record.image_round, record.arch]
    .filter(Boolean)
    .join(' / ');
}

export function formatDataDisks(count: null | number, size: null | number) {
  if (!count) return '无';
  return `${count} x ${size ?? 50}G`;
}

export function formatVNCAddress(host?: null | string, port?: null | number) {
  if (!host || !port) return '';
  return `${host}:${port}`;
}

export function parseHostFromUrl(url?: null | string) {
  if (!url) return '';
  try {
    return new URL(url).hostname;
  } catch {
    return '';
  }
}

export function vmConsoleTabTitle(record: ResourceRecord) {
  return (
    formatVNCAddress(record.host_primary_ip, record.vnc_port) ||
    record.vm_name ||
    record.primary_ip ||
    'VM 控制台'
  );
}

export function vmConsoleConfigTitle(
  config: null | VMConsoleRecord,
  fallback = 'VM 控制台',
) {
  if (!config) return fallback;
  return (
    formatVNCAddress(parseHostFromUrl(config.url), config.port) ||
    config.vm_name ||
    fallback
  );
}

export function canReleaseVM(record: ResourceRecord, context: VMAuthContext) {
  if (!record.current_lease_id) return false;
  if (record.current_lease_user_id === context.currentUserId) return true;
  if (context.currentRole === 'ADMIN') return true;
  return (
    context.currentRole === 'TSE' && record.current_lease_user_role === 'TE'
  );
}

export function canRenewVM(
  record: ResourceRecord,
  context: VMAuthContext,
  now = dayjs(),
) {
  if (
    !record.current_lease_id ||
    !record.current_lease_expected_ends_at ||
    record.current_lease_user_id !== context.currentUserId
  ) {
    return false;
  }
  return dayjs(record.current_lease_expected_ends_at).isBefore(
    now.add(7, 'day'),
  );
}

export function canViewVMCredentials(
  record: ResourceRecord,
  context: VMAuthContext,
) {
  if (!record.has_ssh_password) return false;
  if (context.currentRole === 'ADMIN') return true;
  return record.current_lease_user_id === context.currentUserId;
}

export function canOpenVMConsole(
  record: ResourceRecord,
  context: VMAuthContext,
) {
  if (context.currentRole === 'ADMIN') return true;
  return record.current_lease_user_id === context.currentUserId;
}

export function canRefreshVMIp(record: ResourceRecord, context: VMAuthContext) {
  if (!record.mac_address) return false;
  if (context.currentRole === 'ADMIN') return true;
  return record.current_lease_user_id === context.currentUserId;
}

export function canEditVMCredentials(
  record: ResourceRecord,
  context: VMAuthContext,
) {
  if (context.currentRole === 'ADMIN') return true;
  if (context.currentRole !== 'TSE') return false;
  if (record.management_status !== 'active') return false;
  return (
    !record.current_lease_id ||
    record.current_lease_user_id === context.currentUserId
  );
}
