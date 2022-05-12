import { ref,watch,nextTick } from 'vue';
const detail = ref({});
const drawerShow = ref(false);
const active = ref(false);
const requestCard = ref(null);
const cardInfo = ref([
  { progress: 50, description: '12sadadcxcsdffffffffff232134214asdsfsf', id: 1 },
  { progress: 60, description: '12sadadcxcsdffffffffff232134214asdsfsf', id: 2 },
  { progress: 80, description: '12sadadcxcsdffffffffff232134214asdsfsf', id: 3 },
]);
function cardClick (index) {
  console.log(cardInfo.value[index]);
  active.value = true;
}
const activeTab = ref('testProgress');
const testProgressList = ref([
  {
    title: 'openEuler 22.03 LTS realese', children: [
      { title: '安全测试', progress: 80, list: [{ name: 123, success: false }] },
      { title: '单包服务', progress: 100, list: [{ name: 23, success: false }, { name: 33, success: true }] },
      { title: '单包命令', progress: 80 },
    ],
    id: 1
  },
  {
    title: 'openEuler 22.03 LTS realese', children: [
      { title: '安全测试', progress: 80, list: [{ name: 123, success: false }] },
      { title: '单包服务', progress: 100, list: [{ name: 23, success: false }, { name: 33, success: true }] },
      { title: '单包命令', progress: 80 },
    ],
    id: 2
  }
]);
const newRequestCount = ref(20);
const extendRequestCount = ref(13);
const newRequestRate = ref(80);
const extendRequestRate = ref(100);
const showList = ref();

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
    packageWidth.value = packageBox.value.$el.clientWidth;
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
  cardInfo,
  cardClick,
};
