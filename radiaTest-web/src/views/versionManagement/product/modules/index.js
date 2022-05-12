import * as filter from './productFilter';
import * as productTable from './productTable';
import * as productDetailDrawer from './productDetailDrawer';
export const modules = {
  ...filter,
  ...productTable,
  ...productDetailDrawer
};
