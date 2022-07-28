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
const newRequestCount = ref(0);
const extendRequestCount = ref(0);
const newRequestRate = ref(0);
const extendRequestRate = ref(0);
const showList = ref(false);

const boxWidth = ref(0);
watch(showList, () => {
  nextTick(() => {
    boxWidth.value = requestCard.value.$el.clientWidth;
  });
});
const oldPackage = ref({
  size: 0,
  name: null
});
const newPackage = ref({
  size: 0,
  name: null
});
const showPackage = ref(false);
const packageBox = ref(null);
const packageWidth = ref(0);
watch(showPackage, () => {
  nextTick(() => {
    packageWidth.value = requestCard.value.$el.clientWidth;
  });
});
function handleListClick() {
  showList.value = true;
}
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
  handleListClick,
};
