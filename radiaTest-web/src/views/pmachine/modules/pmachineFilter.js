import { ref } from 'vue';

const filterValue = ref({
  mac: '',
  frame: null,
  _state: null,
  sshIp: '',
  bmcIp: '',
  description: '',
  occupier: '',
});

const clearAll = () => {
  filterValue.value.mac = '';
  filterValue.value.frame = null;
  filterValue.value._state = null;
  filterValue.value.sshIp = '';
  filterValue.value.bmcIp = '';
  filterValue.value.description = '';
  filterValue.value.occupier = '';
};

export default {
  filterValue,
  clearAll,
};
