const requireContext=require.context('../../../../doc/',false,/\.md$/);
const origin=requireContext.keys().map((item,index)=>{
  return {
    id:index,
    title:item.replace('.md','').slice(2),
    tag:'文档'
  };
});
const state = {
  docList: [...origin],
};
const mutations = {
  setNoticeList: (newState, doc) => {
    newState.docList = newState.docList.concat(doc);
  }
};
const actions = {};
export default {
  namespaced: true,
  state,
  mutations,
  actions
};
