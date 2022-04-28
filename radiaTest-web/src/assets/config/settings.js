const name = 'radiaTest';
const version = '1.1.0';
const license = 'Mulan PSL v2';

// const serverIp = ;

// const serverPort = ;

const serverPath = "radiatest.openeuler.org";

const newsSocketPath = `ws://${serverPath}/api/v1/msg`;

export default {
  name,
  version,
  license,
  serverPath,
  serverIp,
  newsSocketPath,
};
