import * as createTask from './createTask.js';
import * as kanbanAndTable from './kanbanAndTable.js';
import * as taskDetail from './taskDetail.js';
import * as mdFile from './mdFile.js';

export const modules = {
  ...createTask,
  ...kanbanAndTable,
  ...taskDetail,
  ...mdFile,
};
