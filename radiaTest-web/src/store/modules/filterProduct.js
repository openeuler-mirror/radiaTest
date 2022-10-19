//版本筛选store缓存

const state = {
  name: null,
  version: null,
  description: null,
  start_time: null,
  end_time: null,
  publish_time: null
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
  },
  setStartTime: (newState, startTime) => {
    newState.start_time = startTime;
  },
  setEndTime: (newState, endTime) => {
    newState.end_time = endTime;
  },
  setPublishTime: (newState, publishTime) => {
    newState.publish_time = publishTime;
  }
};
const actions = {};

export default {
  namespaced: true,
  state,
  mutations,
  actions
};
