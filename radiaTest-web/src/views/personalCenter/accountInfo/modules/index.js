import * as org from './org';
import * as userInfo from './userInfo';
import { showLoading } from '@/assets/utils/loading';

export const modules = {
  ...org,
  ...userInfo,
  showLoading,
};
