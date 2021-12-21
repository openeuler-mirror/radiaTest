const state = {
  data: {}
};
  
const mutations = {
  clear: (newState) => {
    newState.data = {};
  },
  set: (newState, data) => {
    newState.data = data;
  },
};
const actions = {
  
};
  
export default {
  namespaced: true,
  state,
  mutations,
  actions,
};
