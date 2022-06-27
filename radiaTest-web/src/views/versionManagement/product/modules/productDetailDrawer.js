import { ref,watch,nextTick } from 'vue';
const detail = ref({});
const drawerShow = ref(false);
const active = ref(false);
const requestCard = ref(null);
const cardDescription = ref({
  title: null,
  progress: null,
});
function cardClick () {
  active.value = true;
}
const activeTab = ref('testProgress');
const testProgressList = ref([]);
const newRequestCount = ref(20);
const extendRequestCount = ref(13);
const newRequestRate = ref(80);
const extendRequestRate = ref(100);
const showList = ref(false);

const boxWidth = ref(0);
watch(showList, () => {
  nextTick(() => {
    boxWidth.value = requestCard.value.$el.clientWidth;
  });
});
const oldPackage = ref({
  size: 2000,
  name: 'openeuler 20.03 sp3'
});
const newPackage = ref({
  size: 2800,
  name: 'openeuler 20.04 sp4'
});
const showPackage = ref(false);
const packageBox = ref(null);
const packageWidth = ref(0);
watch(showPackage, () => {
  nextTick(() => {
    packageWidth.value = requestCard.value.$el.clientWidth;
  });
});
export {
  packageBox,
  showPackage,
  requestCard,
  newPackage,
  showList,
  oldPackage,
  packageWidth,
  boxWidth,
  newRequestRate,
  extendRequestRate,
  newRequestCount,
  extendRequestCount,
  activeTab,
  active,
  detail,
  testProgressList,
  drawerShow,
  cardDescription,
  cardClick,
};
