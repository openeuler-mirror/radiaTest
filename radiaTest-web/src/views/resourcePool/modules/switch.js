import router from '@/router';
import { ref } from 'vue';
const activeTab = ref('pmachine');
function changeView(value) {
  activeTab.value = value;
  if (value !== 'docker' && router.currentRoute.value.params.machineId) {
    router.push({
      name: value,
      params: {
        machineId: router.currentRoute.value.params.machineId,
      },
    });
  }
}
export { activeTab, changeView };
