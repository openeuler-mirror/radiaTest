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
      if(state.kanban){
        state.kanban = false;
      }else{
        state.kanban = true;
      }
    },
    toggleNewTaskDrawer(state) {
      state.showNewTaskDrawer === true
        ? (state.showNewTaskDrawer = false)
        : (state.showNewTaskDrawer = true);
    },
  },
  actions: {},
};
