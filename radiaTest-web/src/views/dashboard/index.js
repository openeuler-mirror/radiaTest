const modulesFiles = require.context('./modules', true, /\.js$/);
const modules = modulesFiles.keys().reduce((module, modulePath) => {
  const value = modulesFiles(modulePath);
  return Object.assign(module, value);
}, {});
export default modules;
