import { Socket } from '@/socket';
import config from '@/assets/config/settings';

const newsSocket = new Socket(config.newsSocketPath);

const addRoom = (token) => {
  if (newsSocket.isConnect()) {
    newsSocket.emit(
      'after connect', 
      token,
    );
  }
};

export {
  newsSocket,
  addRoom,
};
