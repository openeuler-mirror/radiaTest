import * as addUser from './addUser';
import * as createGroup from './createGroup';
import * as groupDrawer from './groupDrawer';
import * as groupTable from './groupTable';
import * as searchGroup from './searchGroup';
import { showLoading } from '@/assets/utils/loading';

export const modules = {
  ...addUser,
  ...createGroup,
  ...groupDrawer,
  ...groupTable,
  ...searchGroup,
  showLoading,
};
