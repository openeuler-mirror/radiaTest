/*
    通用表单一重选择缓存
    data用以存储实时选择的数据，实现选择受控
    history用以储存选择并删除的数据，用以处理被选项删除后缓存中仍然存在的问题
*/

const state = {
  data: [],
  history: []
};

const actions = {

};

const mutations = {
  setSelectedData: (newState, data) => {
    newState.data = data;
  },
  setDeletedData: (newState, data) => {
    newState.history = newState.history.concat(data);
  }
};

export default {
  namespaced: true,
  state,
  actions,
  mutations
};
