import type { ResourceRecord, VMRequestRecord } from '#/api';

import dayjs from 'dayjs';
import { describe, expect, it } from 'vitest';

import {
  canEditVMCredentials,
  canOpenVMConsole,
  canRefreshVMIp,
  canReleaseVM,
  canRenewVM,
  canViewVMCredentials,
  displayCredentialValue,
  displayValue,
  eventPhaseLabel,
  findRequestedVM,
  formatDataDisks,
  formatRequestImage,
  formatRequestSpec,
  formatSpec,
  formatTaskEventMessage,
  formatVNCAddress,
  installTypeLabel,
  isHostCommandEvent,
  isImportantHostCommand,
  parseHostFromUrl,
  powerActionLabel,
  powerStateColor,
  powerStateLabel,
  shouldDisplayTaskEvent,
  statusColor,
  statusLabel,
  uniqueOptions,
  vmConsoleConfigTitle,
  vmConsoleTabTitle,
} from './vm-view';

function resource(overrides: Partial<ResourceRecord> = {}): ResourceRecord {
  return {
    arch: 'aarch64',
    bmc_ip: null,
    bmc_username: null,
    board_sn: null,
    connectivity_status: 'unknown',
    cpu_count: null,
    cpu_model: null,
    current_lease_expected_ends_at: null,
    current_lease_id: null,
    current_lease_purpose: null,
    current_lease_user_id: null,
    current_lease_user_role: null,
    current_lease_username: null,
    current_test_job_id: null,
    data_disk_count: 0,
    data_disk_paths: [],
    data_disk_size_gb: 50,
    device_distribution: null,
    device_location: null,
    disk_gb: 50,
    extra: {},
    has_bmc_password: false,
    has_ssh_password: true,
    hdd_count: null,
    hdd_spec: null,
    host_primary_ip: '172.168.131.92',
    host_resource_id: null,
    id: 'vm-1',
    is_critical: false,
    kernel_version: null,
    mac_address: '52:54:00:00:00:01',
    management_status: 'active',
    memory_count: null,
    memory_mb: 4096,
    memory_spec: null,
    name: null,
    occupancy_status: 'idle',
    os_version: 'openEuler-24.03-LTS-SP4',
    primary_ip: '172.168.131.201',
    resource_code: 'vm-code',
    resource_type: 'VIRTUAL',
    ssh_username: 'root',
    ssd_card_count: null,
    ssd_card_spec: null,
    ssd_count: null,
    ssd_spec: null,
    system_disk_path: null,
    tags: [],
    test_status: 'idle',
    usage_scenario: null,
    vcpu_count: 2,
    vm_name: 'vm-name',
    vnc_port: 5901,
    vnc_websocket_port: 5701,
    ...overrides,
  };
}

function request(overrides: Partial<VMRequestRecord> = {}): VMRequestRecord {
  return {
    arch: 'aarch64',
    cancelled_at: null,
    completed_at: null,
    created_at: '2026-07-13T00:00:00.000Z',
    data_disk_count: 0,
    data_disk_size_gb: 50,
    dist: 'openEuler',
    error_code: null,
    error_message: null,
    expected_ends_at: null,
    extra_nic_num: 0,
    host_attempts: [],
    host_resource_id: null,
    id: 'request-1',
    image_round: 'round-9',
    image_url: '',
    install_type: 'auto',
    kernel_version: null,
    memory_mb: 4096,
    os_version: 'openEuler-24.03-LTS-SP4',
    purpose: '调试',
    requester_user_id: 'user-1',
    requester_username: 'te1',
    resource_id: null,
    status: 'pending',
    updated_at: '2026-07-13T00:00:00.000Z',
    vcpu_count: 2,
    ...overrides,
  };
}

describe('vm display helpers', () => {
  it('resolves a requested VM only from the current list', () => {
    const vm = resource({ id: 'current-vm' });

    expect(findRequestedVM([vm], 'current-vm')).toBe(vm);
    expect(findRequestedVM([vm], 'stale-vm')).toBeNull();
    expect(findRequestedVM([vm], null)).toBeNull();
  });

  it('formats empty values, specs, images, and disks', () => {
    expect(displayValue('')).toBe('-');
    expect(formatSpec(resource())).toBe('2C / 4G / 50G');
    expect(formatRequestSpec(request())).toBe('2C / 4G');
    expect(formatRequestImage(request({ image_round: '' }))).toBe(
      'openEuler / openEuler-24.03-LTS-SP4 / aarch64',
    );
    expect(formatDataDisks(0, 50)).toBe('无');
    expect(formatDataDisks(2, null)).toBe('2 x 50G');
    expect(formatVNCAddress('172.168.131.92', 5924)).toBe(
      '172.168.131.92:5924',
    );
    expect(formatVNCAddress('172.168.131.92', null)).toBe('');
    expect(parseHostFromUrl('ws://172.168.131.92:5700/')).toBe(
      '172.168.131.92',
    );
    expect(uniqueOptions(['x86_64', '', 'aarch64', 'x86_64'])).toEqual([
      { label: 'aarch64', value: 'aarch64' },
      { label: 'x86_64', value: 'x86_64' },
    ]);
  });

  it('formats status, install type, and credentials', () => {
    expect(statusColor('pending')).toBe('blue');
    expect(statusColor('failed')).toBe('red');
    expect(statusLabel('creating')).toBe('创建中');
    expect(statusLabel('unknown')).toBe('unknown');
    expect(installTypeLabel('manual')).toBe('手动');
    expect(powerActionLabel('reboot')).toBe('重启');
    expect(powerStateLabel('running')).toBe('运行中');
    expect(powerStateLabel('shut off')).toBe('已关机');
    expect(powerStateColor('running')).toBe('green');
    expect(powerStateColor('crashed')).toBe('red');
    expect(displayCredentialValue(false, true, false, null)).toBe('未保存');
    expect(displayCredentialValue(true, false, false, 'secret')).toBe('***');
    expect(displayCredentialValue(true, true, true, 'secret')).toBe(
      '加载中...',
    );
    expect(displayCredentialValue(true, true, false, 'secret')).toBe('secret');
  });

  it('formats task event phases and compact host output', () => {
    expect(eventPhaseLabel('host_command')).toBe('宿主命令');
    expect(eventPhaseLabel('custom_phase')).toBe('custom_phase');
    expect(isHostCommandEvent('host_command')).toBe(true);
    expect(isHostCommandEvent('host_command_failed')).toBe(true);
    expect(isHostCommandEvent('host_command_stderr')).toBe(true);
    expect(isHostCommandEvent('capacity_check')).toBe(false);
    expect(isImportantHostCommand('nproc')).toBe(false);
    expect(isImportantHostCommand('free -m')).toBe(false);
    expect(isImportantHostCommand('virsh define /tmp/domain.xml')).toBe(true);
    expect(isImportantHostCommand('qemu-img create disk.qcow2 50G')).toBe(true);
    expect(isImportantHostCommand('virt-install --name vm-name')).toBe(true);
    expect(shouldDisplayTaskEvent('host_command', 'nproc')).toBe(false);
    expect(shouldDisplayTaskEvent('host_command', 'virsh start vm-name')).toBe(
      true,
    );
    expect(shouldDisplayTaskEvent('host_command_failed')).toBe(true);
    expect(shouldDisplayTaskEvent('check_capacity')).toBe(true);
    expect(formatTaskEventMessage(String.raw`line1\nline2`)).toBe(
      'line1\nline2',
    );
  });

  it('formats console tab titles from VNC address or fallback values', () => {
    expect(vmConsoleTabTitle(resource())).toBe('172.168.131.92:5901');
    expect(
      vmConsoleTabTitle(
        resource({ host_primary_ip: null, primary_ip: '172.168.131.201' }),
      ),
    ).toBe('vm-name');
    expect(
      vmConsoleConfigTitle(
        {
          password: null,
          port: 5924,
          resource_id: 'vm-1',
          url: 'ws://172.168.131.92:5700/',
          vm_name: 'vm-name',
          websocket_port: 5700,
        },
        'fallback',
      ),
    ).toBe('172.168.131.92:5924');
    expect(vmConsoleConfigTitle(null, 'fallback')).toBe('fallback');
  });
});

describe('vm permission helpers', () => {
  it('lets admins act on any VM', () => {
    const vm = resource();
    const context = { currentRole: 'ADMIN' as const, currentUserId: 'admin' };

    expect(canViewVMCredentials(vm, context)).toBe(true);
    expect(canOpenVMConsole(vm, context)).toBe(true);
    expect(canRefreshVMIp(vm, context)).toBe(true);
    expect(canEditVMCredentials(vm, context)).toBe(true);
  });

  it('allows owners to view credentials, open console, refresh ip, release and renew', () => {
    const vm = resource({
      current_lease_expected_ends_at: '2026-07-15T00:00:00.000Z',
      current_lease_id: 'lease-1',
      current_lease_user_id: 'user-1',
    });
    const context = { currentRole: 'TE' as const, currentUserId: 'user-1' };

    expect(canViewVMCredentials(vm, context)).toBe(true);
    expect(canOpenVMConsole(vm, context)).toBe(true);
    expect(canReleaseVM(vm, context)).toBe(true);
    expect(canRenewVM(vm, context, dayjs('2026-07-13T00:00:00.000Z'))).toBe(
      true,
    );
    expect(canRefreshVMIp(vm, context)).toBe(true);
  });

  it('prevents non-owners from viewing credentials or opening console', () => {
    const vm = resource({
      current_lease_id: 'lease-1',
      current_lease_user_id: 'user-2',
    });
    const context = { currentRole: 'TE' as const, currentUserId: 'user-1' };

    expect(canViewVMCredentials(vm, context)).toBe(false);
    expect(canOpenVMConsole(vm, context)).toBe(false);
    expect(canReleaseVM(vm, context)).toBe(false);
    expect(canRefreshVMIp(vm, context)).toBe(false);
  });

  it('allows TSE to force release only a TE lease', () => {
    const context = { currentRole: 'TSE' as const, currentUserId: 'tse-1' };

    expect(
      canReleaseVM(
        resource({
          current_lease_id: 'lease-1',
          current_lease_user_id: 'te-1',
          current_lease_user_role: 'TE',
        }),
        context,
      ),
    ).toBe(true);
    for (const role of ['ADMIN', 'TSE'] as const) {
      expect(
        canReleaseVM(
          resource({
            current_lease_id: 'lease-1',
            current_lease_user_id: 'other-user',
            current_lease_user_role: role,
          }),
          context,
        ),
      ).toBe(false);
    }
  });

  it('allows TSE to edit idle or own active VM credentials only', () => {
    const context = { currentRole: 'TSE' as const, currentUserId: 'tse-1' };

    expect(canEditVMCredentials(resource(), context)).toBe(true);
    expect(
      canEditVMCredentials(
        resource({
          current_lease_id: 'lease-1',
          current_lease_user_id: 'tse-1',
        }),
        context,
      ),
    ).toBe(true);
    expect(
      canEditVMCredentials(
        resource({
          current_lease_id: 'lease-1',
          current_lease_user_id: 'other-user',
        }),
        context,
      ),
    ).toBe(false);
    expect(
      canEditVMCredentials(
        resource({ management_status: 'maintenance' }),
        context,
      ),
    ).toBe(false);
  });
});
