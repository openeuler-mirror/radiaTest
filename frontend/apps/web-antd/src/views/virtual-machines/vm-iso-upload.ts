export const MAX_VM_ISO_BYTES = 20 * 1024 ** 3;

interface UploadFileLike {
  name: string;
  size: number;
}

export function validateVMISOFile(file: UploadFileLike) {
  if (!file.name.toLowerCase().endsWith('.iso')) {
    return '请选择 ISO 文件';
  }
  if (file.size <= 0) {
    return 'ISO 文件不能为空';
  }
  if (file.size > MAX_VM_ISO_BYTES) {
    return 'ISO 文件不能超过 20 GB';
  }
  return null;
}

export function resolveVMISOUrl(path: string, origin: string) {
  return new URL(path, origin).toString();
}
