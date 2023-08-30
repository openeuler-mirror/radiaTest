const requireContext=require.context('../../../../notice/',false,/\.md$/);
const origin=requireContext.keys().map((item,index)=>{
  return {
    id:index,
    title:item.replace('.md','').slice(2),
    tag:'公告'
  };
});
const state = {
  noticeList: [...origin],
};
const mutations = {
  setNoticeList: (newState, notice) => {
    newState.noticeList = newState.noticeList.concat(notice);
  }
};
const actions = {};
export default {
  namespaced: true,
  state,
  mutations,
  actions
};
