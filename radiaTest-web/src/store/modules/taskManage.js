export default {
  namespaced: true,
  state() {
    return {
      kanban: true, //看板视图、表格视图切换
      showNewTaskDrawer: false, //新建任务抽屉
    };
  },
  getters: {},
  mutations: {
    toggleView(state) {
      state.kanban === true ? (state.kanban = false) : (state.kanban = true);
    },
    toggleNewTaskDrawer(state) {
      state.showNewTaskDrawer === true
        ? (state.showNewTaskDrawer = false)
        : (state.showNewTaskDrawer = true);
    },
  },
  actions: {},
};
