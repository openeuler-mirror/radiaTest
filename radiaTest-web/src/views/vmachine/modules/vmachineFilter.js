import { ref } from 'vue';

const filterValue = ref({
  name: '',
  frame: null,
  ip: '',
  host_ip: '',
  description: '',
});

const clearAll = () => {
  filterValue.value = {
    name: '',
    frame: null,
    ip: '',
    host_ip: '',
    description: '',
  };
};

export default {
  filterValue,
  clearAll,
};
