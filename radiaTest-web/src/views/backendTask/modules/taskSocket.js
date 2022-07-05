import { getTask } from './taskTable';

function connectSocket(socketObj) {
  socketObj.connect();
  socketObj.listen('update', () => {
    getTask();
  });
}
function disconnectSocket(socketObj) {
  socketObj.disconnect();
}

export { connectSocket, disconnectSocket };
