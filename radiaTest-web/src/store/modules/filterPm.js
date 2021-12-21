//物理机筛选store缓存

const state = {
  mac: '',
  frame: null,
  state: null,
  ip: '',
  bmc_ip: '',
  occupier: '',
  description: ''
};
const mutations = {
  setAll: (newState, filterValue) => {
    newState.mac = filterValue.mac;
    newState.frame = filterValue.frame;
    newState.state = filterValue._state;
    newState.ip = filterValue.sshIp;
    newState.bmc_ip = filterValue.bmcIp;
    newState.occupier = filterValue.occupier;
    newState.description = filterValue.description;
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
