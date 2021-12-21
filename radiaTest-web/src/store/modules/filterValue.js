//模糊筛选store缓存

const state = {
  value: '',
};
const mutations = {
  setValue: (newState, value) => {
    newState.value = value;
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
