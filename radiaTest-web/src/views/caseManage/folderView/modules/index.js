import * as menu from './menu';
import * as create from './createRef';
import { showLoading } from '@/assets/utils/loading';
import * as editRef from './editRef';

export const modules = {
  showLoading,
  ...menu,
  ...create,
  ...editRef,
};
