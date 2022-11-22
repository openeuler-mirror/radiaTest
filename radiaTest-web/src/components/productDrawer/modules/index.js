import * as collapseTable from './collapseTable';
import * as qualityProject from './qualityProtect';
import * as atOverview from './atOverview';
import * as dailyBuild from './dailyBuild';
import * as weeklybuildHealth from './weeklybuildHealth';
export const modules = {
  ...collapseTable,
  ...qualityProject,
  ...atOverview,
  ...dailyBuild,
  ...weeklybuildHealth,
};
