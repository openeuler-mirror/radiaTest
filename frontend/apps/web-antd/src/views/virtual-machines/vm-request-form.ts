import type { Dayjs } from 'dayjs';

import type { VMRequestPayload } from '#/api';

export type VMInstallType = 'auto' | 'manual';

export interface VMRequestFormState {
  archSelections: string[];
  aarch64Count: number;
  x86_64Count: number;
  dataDiskCount: number;
  dist: string;
  expectedEndsAt?: Dayjs;
  extraNicNum: number;
  imageRound: string;
  imageUrl: string;
  installType: VMInstallType;
  memoryMb: number;
  osVersion: string;
  permanent: boolean;
  purpose: string;
  vcpuCount: number;
  kernelVariant: string;
  kernelRpmUrl: string;
}

export type VMRequestField =
  | 'aarch64Count'
  | 'archSelections'
  | 'dataDiskCount'
  | 'dist'
  | 'expectedEndsAt'
  | 'imageRound'
  | 'imageUrl'
  | 'installType'
  | 'memoryMb'
  | 'osVersion'
  | 'purpose'
  | 'vcpuCount'
  | 'x86_64Count';

export function isVMRequestFieldRequired(
  field: VMRequestField,
  form: VMRequestFormState,
  isAdmin: boolean,
) {
  if (field === 'archSelections') return true;
  if (field === 'imageRound') return form.installType === 'auto';
  if (field === 'imageUrl') return form.installType === 'manual';
  if (field === 'expectedEndsAt') return !isAdmin || !form.permanent;
  return (
    field === 'dist' ||
    field === 'installType' ||
    field === 'memoryMb' ||
    field === 'osVersion' ||
    field === 'purpose' ||
    field === 'vcpuCount'
  );
}

export function validateVMRequestForm(
  form: VMRequestFormState,
  isAdmin: boolean,
) {
  const dist = form.dist.trim();
  const imageRound = form.imageRound.trim();
  const imageUrl = form.imageUrl.trim();
  const isManual = form.installType === 'manual';
  const osVersion = form.osVersion.trim();
  const purpose = form.purpose.trim();

  if (!dist || !osVersion) {
    return '请填写发行版、OS 版本';
  }
  if (form.archSelections.length === 0) {
    return '请至少选择一个架构';
  }
  const total = form.archSelections.reduce((sum, arch) => {
    return sum + (arch === 'aarch64' ? form.aarch64Count : form.x86_64Count);
  }, 0);
  if (total === 0) {
    return '请至少为选中的架构设置数量';
  }
  if (isManual) {
    try {
      const url = new URL(imageUrl);
      if (!['http:', 'https:'].includes(url.protocol)) {
        throw new Error('unsupported protocol');
      }
    } catch {
      return '请输入 HTTP/HTTPS ISO URL';
    }
  } else if (!imageRound) {
    return '请选择镜像轮次';
  }
  if (!purpose) {
    return '请填写用途';
  }
  if (!isAdmin && !form.expectedEndsAt) {
    return '请选择租约截止时间';
  }
  return null;
}

export function buildVMRequestPayload(
  form: VMRequestFormState,
  isAdmin: boolean,
): VMRequestPayload {
  const isManual = form.installType === 'manual';
  return {
    arch: form.archSelections[0] || 'aarch64',
    data_disk_count: form.dataDiskCount,
    dist: form.dist.trim(),
    expected_ends_at:
      isAdmin && form.permanent ? null : form.expectedEndsAt?.toISOString(),
    extra_nic_num: form.extraNicNum,
    image_round: form.imageRound.trim(),
    image_url: isManual ? form.imageUrl.trim() : null,
    install_type: form.installType,
    memory_mb: form.memoryMb,
    os_version: form.osVersion.trim(),
    purpose: form.purpose.trim(),
    vcpu_count: form.vcpuCount,
    kernel_variant: form.kernelVariant || null,
    kernel_rpm_url: form.kernelRpmUrl.trim() || null,
  };
}
