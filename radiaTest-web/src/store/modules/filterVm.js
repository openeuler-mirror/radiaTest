//虚拟机筛选store缓存

const state = {
  name: '',
  ip: '',
  frame: null,
  host_ip: '',
  description: '',
};
const mutations = {
  setAll: (newState, data) => {
    newState.name = data.name;
    newState.frame = data.frame;
    newState.ip = data.ip;
    newState.host_ip = data.host_ip;
    newState.description = data.description;
  },
};
const actions = {

};

export default {
  namespaced: true,
  state,
  mutations,
  actions
};
