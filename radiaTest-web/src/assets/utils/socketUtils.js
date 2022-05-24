import { Socket } from '@/socket';
import config from '@/assets/config/settings';

const newsSocket = new Socket(config.newsSocketPath);

const addRoom = (_token) => {
  if (newsSocket.isConnect()) {
    newsSocket.emit(
      'after_connect', 
      {
        'sid': newsSocket.socket.id,
        'token': _token,
      }
    );
  }
};

export {
  newsSocket,
  addRoom,
};
