import { showLoading } from '@/assets/utils/loading';
import * as login from './login';
import * as org from './org';

export const modules = {
  ...login,
  ...org,
  showLoading
};
