import { ref } from 'vue';

const filterValue = ref({
  suite: '',
  name: '',
  test_level: null,
  test_type: null,
  machine_num: '',
  machine_type: null,
  automatic: null,
  remark: '',
  owner: '',
});

const clearAll = () => {
  filterValue.value.suite = '';
  filterValue.value.name = '';
  filterValue.value.test_level = null;
  filterValue.value.test_type = null;
  filterValue.value.machine_num = '';
  filterValue.value.machine_type = null;
  filterValue.value.automatic = null;
  filterValue.value.remark = '';
  filterValue.value.owner = '';
};

export default {
  filterValue,
  clearAll,
};
