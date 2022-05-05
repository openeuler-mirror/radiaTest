import * as org from './org';
import * as userInfo from './userInfo';
import { showLoading } from '@/assets/utils/loading';
import * as orgDrawer from './orgDrawer';

export const modules = {
  ...org,
  ...userInfo,
  ...orgDrawer,
  showLoading,
};
