import * as productTable from './collapseTable';
import * as qualityProject from './qualityProtect';
import * as atOverview from './atOverview';
import * as dailyBuild from './dailyBuild';
import * as weeklybuildHealth from './weeklybuildHealth';
export const modules = {
  ...productTable,
  ...qualityProject,
  ...atOverview,
  ...dailyBuild,
  ...weeklybuildHealth,
};
