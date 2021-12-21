//测试用例筛选store缓存

const state = {
  suite: '',
  name: '',
  test_level: null,
  test_type: null,
  machine_num: '',
  machine_type: null,
  automatic: null,
  remark: '',
  owner: ''
};
const mutations = {
  setAll: (newState, filterValue) => {
    newState.suite = filterValue.suite;
    newState.name = filterValue.name;
    newState.test_level = filterValue.test_level;
    newState.test_type = filterValue.test_type;
    newState.machine_num = filterValue.machine_num;
    newState.machine_type = filterValue.machine_type;
    newState.automatic = filterValue.automatic;
    newState.remark = filterValue.remark;
    newState.owner = filterValue.owner;
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
  
