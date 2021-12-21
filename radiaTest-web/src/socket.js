//定义socket类
import socketIO from 'socket.io-client';

class Socket {
  constructor(url) {
    this.url = url;
  }
  connect() {
    this.socket = socketIO.connect(this.url, { transports: ['websocket'] });
  }
  disconnect() {
    this.socket.close();
  }
  isConnect() {
    return this.socket && this.socket.connected;
  }
  emit(event, data) {
    this.socket.emit(event, data);
  }
  listen(event, callback) {
    this.socket.on(event, (data) => {
      callback && callback(data);
    });
  }
}

export {
  Socket,
};
