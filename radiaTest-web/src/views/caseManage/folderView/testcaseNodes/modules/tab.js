import { ref } from 'vue';

const activeTab = ref('details');
function tabChange (value) {
  activeTab.value = value;
}

export {
  activeTab,
  tabChange
};
