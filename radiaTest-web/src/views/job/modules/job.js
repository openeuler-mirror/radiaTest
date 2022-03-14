import { ref } from 'vue';
const totalData = ref([]);
const logsDrawer = ref(null);
const createButton = ref(null);
const createModalRef = ref(null);
const createFormRef = ref(null);

const changeTimeFormat = (data) => {
  if(Array.isArray(data)){
    data.forEach((item) => {
      if (item.multiple) {
        item.children = [{}];
      }
      item.start_time
        ? (item.start_time = new Date(item.start_time)
          .toLocaleString('zh-CN', { hourCycle: 'h23' })
          .replace(/\//g, '-'))
        : 0;
      item.end_time
        ? (item.end_time = new Date(item.end_time)
          .toLocaleString('zh-CN', { hourCycle: 'h23' })
          .replace(/\//g, '-'))
        : 0;
      item.create_time = new Date(item.create_time).getTime();
    });
    return data;
  }
  return [];
};

const execData = ref([]);

const waitData = ref([]);

const finishData = ref([]);

const handleHover = (button) => {
  button.style.cursor = 'pointer';
  button.style.color = 'grey';
};
const handleLeave = (button) => {
  button.style.color = 'rgba(206, 206, 206, 1)';
};

const devideData = (res) => {
  execData.value = res.filter(
    (item) =>
      item.status !== 'DONE' &&
      item.status !== 'BLOCK' &&
      item.status !== 'PENDING'
  );
  waitData.value = res.filter((item) => item.status === 'PENDING');
  finishData.value = res.filter(
    (item) => item.status === 'DONE' || item.status === 'BLOCK'
  );
};

export default {
  logsDrawer,
  totalData,
  execData,
  waitData,
  finishData,
  createButton,
  changeTimeFormat,
  handleHover,
  handleLeave,
  createModalRef,
  createFormRef,
  devideData,
};
