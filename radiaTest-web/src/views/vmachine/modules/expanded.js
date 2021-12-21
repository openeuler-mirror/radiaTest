import { ref } from 'vue';

const handleChange = (memoryPercentage, cpuPercentage) => {
  memoryPercentage.value = 0;
  cpuPercentage.value = 0;
};

const createFormNic= ref(null);
const createModalNic = ref(null);

const createFormDisk= ref(null);
const createModalDisk = ref(null);

const nics = ref(null);
const disks = ref(null);

const editModalRef = ref(null);

export default {
  handleChange,
  createFormNic,
  createModalNic,
  createFormDisk,
  createModalDisk,
  nics,
  disks,
  editModalRef,
};

