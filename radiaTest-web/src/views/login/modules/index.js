import { showLoading } from '@/assets/utils/loading';
import * as claSign from './claSign';
import * as login from './login';
import * as majunIframe from './majunIframe';
import * as org from './org';

export const modules = {
  ...claSign,
  ...login,
  ...majunIframe,
  ...org,
  showLoading
};
