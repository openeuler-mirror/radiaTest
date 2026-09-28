import { describe, expect, it } from 'vitest';

import {
  MAX_VM_ISO_BYTES,
  resolveVMISOUrl,
  validateVMISOFile,
} from './vm-iso-upload';

describe('validateVMISOFile', () => {
  it('accepts a non-empty ISO within the size limit', () => {
    expect(validateVMISOFile({ name: 'openEuler.ISO', size: 1024 })).toBeNull();
  });

  it('rejects invalid extensions, empty files, and oversized files', () => {
    expect(validateVMISOFile({ name: 'image.qcow2', size: 1 })).toBe(
      '请选择 ISO 文件',
    );
    expect(validateVMISOFile({ name: 'image.iso', size: 0 })).toBe(
      'ISO 文件不能为空',
    );
    expect(
      validateVMISOFile({ name: 'image.iso', size: MAX_VM_ISO_BYTES + 1 }),
    ).toBe('ISO 文件不能超过 20 GB');
  });
});

describe('resolveVMISOUrl', () => {
  it('turns the backend relative path into a host-reachable URL', () => {
    expect(
      resolveVMISOUrl('/vm-iso/abc.iso', 'http://172.168.131.17:8080/current'),
    ).toBe('http://172.168.131.17:8080/vm-iso/abc.iso');
  });
});
