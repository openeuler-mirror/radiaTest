//定义socket类
import socketIO from 'socket.io-client';

class Socket {
  constructor(url, query) {
    this.url = url;
    this.query = query;
  }
  connect() {
    this.socket = socketIO.connect(this.url, {
      transports: ['websocket'],
      query: this.query,
    });
    this.sessionID = this.socket.sessionId;
  }
  disconnect() {
    this.socket.close();
  }
  isConnect() {
    return this.socket?.connected;
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

export { Socket };
