export default {
  namespaced: true,
  state() {
    return {
      kanban: true, //泳道视图、甘特视图切换
      showNewTaskDrawer: false, //新建任务抽屉
    };
  },
  getters: {},
  mutations: {
    toggleView(state) {
      state.kanban = !state.kanban;
    },
    toggleNewTaskDrawer(state) {
      state.showNewTaskDrawer === true
        ? (state.showNewTaskDrawer = false)
        : (state.showNewTaskDrawer = true);
    },
  },
  actions: {},
};
