import * as role from './role';
import * as rule from './rules';
import { showLoading } from '@/assets/utils/loading';

export const modules = {
  showLoading,
  ...role,
  ...rule,
};
