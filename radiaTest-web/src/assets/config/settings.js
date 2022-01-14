const name = 'radiaTest';
const version = '1.1.0';
const license = 'Mulan PSL v2';

const serverIp = '123.60.114.22';

const serverPort = 1401;

const serverPath = `${serverIp}:${serverPort}`;

const newsSocketPath = `ws://${serverIp}:${serverPort}/api/v1/msg`;

export default {
  name,
  version,
  license,
  serverPath,
  serverIp,
  newsSocketPath,
};
