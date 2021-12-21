const name = 'radiaTest';
const version = '1.1.0';
const license = 'Mulan PSL v2';

// const serverIp = xxxx;

// const serverPort = xxxx;

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
