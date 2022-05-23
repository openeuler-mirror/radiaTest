import { Socket } from '@/socket';
import config from '@/assets/config/settings';
import { getTask } from './taskTable';
function connectSocket() {
  const socketObj = new Socket(`${config.websocketProtocol}://${config.serverPath}/celerytask`);
  console.log('connect');
  socketObj.connect();
  socketObj.listen('update', () => {
    getTask();
  });
}

export { connectSocket };
