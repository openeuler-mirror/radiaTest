const state = {
  unLoginOrgId: {},
};

const actions = {

};

const mutations = {
  setOrgId: (newState, data) => {
    newState.unLoginOrgId = data;
  },

};

export default {
  namespaced: true,
  state,
  actions,
  mutations
};
