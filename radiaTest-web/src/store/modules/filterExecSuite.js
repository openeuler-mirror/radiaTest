//测试套筛选store缓存

const state = {
  suite: '',
  description: '',
  _class: '',
  subClass: '',
  owner: ''
};
const mutations = {
  setSuite: (newState, suite) => {
    newState.suite = suite;
  },
  setDescription: (newState, description) => {
    newState.description = description;
  },
  setClass: (newState, _class) => {
    newState._class = _class;
  },
  setSubClass: (newState, subClass) => {
    newState.subClass = subClass;
  },
  setOwner: (newState, owner) => {
    newState.owner = owner;
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
