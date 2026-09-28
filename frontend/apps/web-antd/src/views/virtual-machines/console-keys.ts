export interface CtrlAltTarget {
  code: string;
  keysym: number;
  label: string;
  value: string;
}

export interface VNCKeyStroke {
  code: string;
  down?: boolean;
  keysym: number;
}

const XK_CONTROL_L = 65_507;
const XK_ALT_L = 65_513;

export const ctrlAltTargets: CtrlAltTarget[] = [
  { code: 'F1', keysym: 65_470, label: 'F1', value: 'F1' },
  { code: 'F2', keysym: 65_471, label: 'F2', value: 'F2' },
  { code: 'F3', keysym: 65_472, label: 'F3', value: 'F3' },
  { code: 'F4', keysym: 65_473, label: 'F4', value: 'F4' },
  { code: 'F5', keysym: 65_474, label: 'F5', value: 'F5' },
  { code: 'F6', keysym: 65_475, label: 'F6', value: 'F6' },
  { code: 'Delete', keysym: 65_535, label: 'Del', value: 'Del' },
];

export function buildCtrlAltKeySequence(
  targetValue: string,
): null | VNCKeyStroke[] {
  const target = ctrlAltTargets.find((item) => item.value === targetValue);
  if (!target) return null;
  return [
    { code: 'ControlLeft', down: true, keysym: XK_CONTROL_L },
    { code: 'AltLeft', down: true, keysym: XK_ALT_L },
    { code: target.code, keysym: target.keysym },
    { code: 'AltLeft', down: false, keysym: XK_ALT_L },
    { code: 'ControlLeft', down: false, keysym: XK_CONTROL_L },
  ];
}
