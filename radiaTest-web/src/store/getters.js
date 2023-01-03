const getters = {
  getRowData: state => state.rowData.data,
  filterVmState: state => state.filterVm,
  filterPmState: state => state.filterPm,
  filterMilestoneState: state => state.filterValue,
  filterMirrorState: state => state.filterValue,
  filterCaseState: state => state.filterCase,
  filterExecSuiteState: state => state.filterExecSuite,
  selectedData: state => state.selected.data,
  deletedData: state => state.selected.history,
  getReadNewsList: state => state.news.readNewsList,
  getUnreadNewsList: state => state.news.unreadNewsList,
};
export default getters;
