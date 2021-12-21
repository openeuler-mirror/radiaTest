import { createStore } from 'vuex';
import getters from './getters';

//获取store模块所在目录的上下文
const modulesFiles = require.context('./modules', true, /\.js$/);

const modules = modulesFiles.keys().reduce((_modules, modulePath) => {
  //取module的名字
  const moduleName = modulePath.replace(/^\.\/(.*)\.\w+$/, '$1');
  //用模块地址在目录上下文中获取require对象
  const value = modulesFiles(modulePath);
  //生成符合引用格式的modules字典
  _modules[moduleName] = value.default;
  return _modules;
}, {});

export default createStore({
  getters,
  modules
});
