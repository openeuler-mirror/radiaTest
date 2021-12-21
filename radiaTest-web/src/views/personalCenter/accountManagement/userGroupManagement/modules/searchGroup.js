import { ref } from 'vue';

import { pagination, getDataList } from './groupTable';

const searchGroupName = ref('');
function searchGroup () {
  pagination.page = 1;
  getDataList(searchGroupName.value);
}

export {
  searchGroupName, searchGroup,
};
