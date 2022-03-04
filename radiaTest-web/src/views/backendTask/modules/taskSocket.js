import { Socket } from '@/socket';
import config from '@/assets/config/settings';
import { getTask } from './taskTable';
let socketObj;
function handleSocket() {
  if (socketObj.isConnect()) {
    socketObj.listen('listen', () => {
      getTask();
    });
  }
}
function connectSocket() {
  socketObj = new Socket(`ws://${config.serverPath}/celerytask`);
  socketObj.connect();
  handleSocket();
}

export { connectSocket };
