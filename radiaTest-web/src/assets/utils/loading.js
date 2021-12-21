import { ref } from 'vue';

const showLoading = ref(false);
function changeLoadingStatus (status) {
  showLoading.value = status;
}
export {
  showLoading,
  changeLoadingStatus,
};
