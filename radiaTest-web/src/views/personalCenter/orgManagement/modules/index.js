import * as logout from './logout';
import * as orgTable from './orgTable';
import * as registerOrg from './registerOrg';
import { showLoading } from '@/assets/utils/loading';

export const modules = { ...logout, ...orgTable, ...registerOrg, showLoading };
