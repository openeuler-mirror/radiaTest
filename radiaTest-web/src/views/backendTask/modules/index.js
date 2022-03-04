import * as taskTable from './taskTable';
import * as connectSocket from './taskSocket';

export const modules = {
  ...taskTable,
  ...connectSocket,
};
