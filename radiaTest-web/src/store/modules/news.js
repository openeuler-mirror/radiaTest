const state = {
  unreadNewsList: [],
  readNewsList: [],
};
const mutations = {
  setUnreadNewsList: (states, value) => {
    states.unreadNewsList = value;
  },
  setReadNewsList: (states, value) => {
    states.readNewsList = value;
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
