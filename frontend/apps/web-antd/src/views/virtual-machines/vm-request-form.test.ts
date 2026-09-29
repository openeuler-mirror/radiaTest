import type { VMRequestFormState } from './vm-request-form';

import dayjs from 'dayjs';
import { describe, expect, it } from 'vitest';

import {
  buildVMRequestPayload,
  isVMRequestFieldRequired,
  validateVMRequestForm,
} from './vm-request-form';

function baseForm(
  overrides: Partial<VMRequestFormState> = {},
): VMRequestFormState {
  return {
    archSelections: ['aarch64'],
    aarch64Count: 1,
    x86_64Count: 0,
    dataDiskCount: 1,
    dist: ' openEuler ',
    expectedEndsAt: dayjs('2026-07-20T08:00:00.000Z'),
    extraNicNum: 2,
    imageRound: ' round-9 ',
    imageUrl: '',
    installType: 'auto',
    memoryMb: 4096,
    osVersion: ' openEuler-24.03-LTS-SP4 ',
    permanent: false,
    purpose: ' 调试 VM ',
    vcpuCount: 2,
    kernelVariant: '',
    kernelRpmUrl: '',
    ...overrides,
  };
}

describe('validateVMRequestForm', () => {
  it('accepts a complete automatic request', () => {
    expect(validateVMRequestForm(baseForm(), false)).toBeNull();
  });

  it('requires image round for automatic requests', () => {
    expect(validateVMRequestForm(baseForm({ imageRound: '' }), false)).toBe(
      '请选择镜像轮次',
    );
  });

  it('allows empty round for manual requests but requires an http iso url', () => {
    expect(
      validateVMRequestForm(
        baseForm({
          imageRound: '',
          imageUrl: 'http://repo.example/openEuler.iso',
          installType: 'manual',
        }),
        false,
      ),
    ).toBeNull();
    expect(
      validateVMRequestForm(
        baseForm({
          imageUrl: 'ftp://repo.example/openEuler.iso',
          installType: 'manual',
        }),
        false,
      ),
    ).toBe('请输入 HTTP/HTTPS ISO URL');
  });

  it('requires a lease deadline for non-admin users', () => {
    expect(
      validateVMRequestForm(baseForm({ expectedEndsAt: undefined }), false),
    ).toBe('请选择租约截止时间');
  });
});

describe('isVMRequestFieldRequired', () => {
  it('marks automatic and manual request fields according to validation rules', () => {
    const automaticForm = baseForm({ installType: 'auto' });
    const manualForm = baseForm({
      imageRound: '',
      imageUrl: 'http://repo.example/openEuler.iso',
      installType: 'manual',
    });

    expect(isVMRequestFieldRequired('dist', automaticForm, false)).toBe(true);
    expect(isVMRequestFieldRequired('imageRound', automaticForm, false)).toBe(
      true,
    );
    expect(isVMRequestFieldRequired('imageUrl', automaticForm, false)).toBe(
      false,
    );
    expect(isVMRequestFieldRequired('imageRound', manualForm, false)).toBe(
      false,
    );
    expect(isVMRequestFieldRequired('imageUrl', manualForm, false)).toBe(true);
  });

  it('does not require a lease deadline for permanent admin requests', () => {
    const form = baseForm({ expectedEndsAt: undefined, permanent: true });

    expect(isVMRequestFieldRequired('expectedEndsAt', form, true)).toBe(false);
    expect(isVMRequestFieldRequired('expectedEndsAt', form, false)).toBe(true);
  });
});

describe('buildVMRequestPayload', () => {
  it('trims text fields and sends automatic request payload', () => {
    expect(buildVMRequestPayload(baseForm(), false)).toEqual({
      arch: 'aarch64',
      data_disk_count: 1,
      dist: 'openEuler',
      expected_ends_at: '2026-07-20T08:00:00.000Z',
      extra_nic_num: 2,
      image_round: 'round-9',
      image_url: null,
      install_type: 'auto',
      memory_mb: 4096,
      os_version: 'openEuler-24.03-LTS-SP4',
      purpose: '调试 VM',
      vcpu_count: 2,
      kernel_variant: null,
      kernel_rpm_url: null,
    });
  });

  it('sends manual request payload with iso url and optional round', () => {
    expect(
      buildVMRequestPayload(
        baseForm({
          imageRound: '',
          imageUrl: ' http://repo.example/openEuler.iso ',
          installType: 'manual',
        }),
        false,
      ),
    ).toMatchObject({
      image_round: '',
      image_url: 'http://repo.example/openEuler.iso',
      install_type: 'manual',
    });
  });

  it('sends null lease deadline for permanent admin requests', () => {
    expect(
      buildVMRequestPayload(
        baseForm({ expectedEndsAt: undefined, permanent: true }),
        true,
      ).expected_ends_at,
    ).toBeNull();
  });
});
