import * as menu from './menu';
import * as createPool from './createPool';
import { showLoading } from '@/assets/utils/loading';
import * as switchTab from './switch';
export const modules = {
  ...menu,
  ...createPool,
  showLoading,
  ...switchTab
};
