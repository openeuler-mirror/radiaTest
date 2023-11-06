import { ref } from 'vue';
const executeRef = ref(null);
const finishRef = ref(null);
const excuteDrawerRef = ref(null);
const resultCountDrawerRef = ref(null);
const manualCreateModalRef = ref(null);
const execData = ref([]);
const finishData = ref([]);

const devideData = (res) => {
  execData.value = res.filter((item) => item.status !== 'DONE' && item.status !== 'BLOCK' && item.status !== 'PENDING');
  finishData.value = res.filter((item) => item.status === 'DONE' || item.status === 'BLOCK');
};
const openCreateManual = () => {
  manualCreateModalRef.value.showModal = true;
};

export default {
  executeRef,
  finishRef,
  excuteDrawerRef,
  resultCountDrawerRef,
  manualCreateModalRef,
  execData,
  finishData,
  devideData,
  openCreateManual,
};
