//版本筛选store缓存

const state = {
  name: '',
  version: '',
  description: '',
};
const mutations = {
  setName: (newState, name) => {
    newState.name = name;
  },
  setVersion: (newState, version) => {
    newState.version = version;
  },
  setDescription: (newState, description) => {
    newState.description = description;
  }
};
const actions = {

};

export default {
  namespaced: true,
  state,
  mutations,
  actions
};
