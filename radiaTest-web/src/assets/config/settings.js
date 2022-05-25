const name = 'radiaTest';
const version = '1.1.0';
const license = 'Mulan PSL v2';


const serverPath = 'radiatest.openeuler.org';
// const serverPath = '0.0.0.0:8080';

const websocketProtocol = 'wss';

const newsSocketPath = `${websocketProtocol}://${serverPath}/message`;

export default {
  name,
  version,
  license,
  serverPath,
  newsSocketPath,
};
