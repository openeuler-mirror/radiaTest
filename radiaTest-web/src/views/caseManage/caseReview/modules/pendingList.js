import { ref } from 'vue';
import { getPendingReview } from '@/api/post';
const pendingModal = ref();
const pendingData = ref([]);
const pendingPage = ref(1);
const pendingPageCount = ref(1);
const pendingRef = ref();
function getPendingData () {
  getPendingReview({page_num:pendingPage.value,page_size:10}).then(res => {
    pendingData.value = res.data.items;
    pendingPageCount.value = res.data.pages;
  });
}
function pendingPageChange (page) {
  pendingPage.value = page;
  getPendingData();
}
function showPendingModal () {
  pendingModal.value.show();
  getPendingData();
}
export {
  pendingModal,
  pendingData,
  pendingPageCount,
  pendingPage,
  pendingRef,
  showPendingModal,
  pendingPageChange,
  getPendingData
};
