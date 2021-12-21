import { ref } from 'vue';
import axios from '@/axios';

const totalData = ref([]);
const logsDrawer = ref(null);
const createButton = ref(null);
const createModalRef = ref(null);
const createFormRef = ref(null);

const changeTimeFormat = (data) => {
  data.forEach((item) => {
    item.start_time
      ? item.start_time = new Date(item.start_time)
        .toLocaleString('zh-CN', {hourCycle: 'h23'})
        .replace(/\//g, '-')
      : 0;
    item.end_time
      ? item.end_time = new Date(item.end_time)
        .toLocaleString('zh-CN', {hourCycle: 'h23'})
        .replace(/\//g, '-')
      : 0;
    item.create_time = new Date(item.create_time).getTime();
  });
  return data;
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
      (item.status !== 'waiting' && item.status !== 'done' && item.status !== 'block') ||
      (item.status === 'done' && item.result === null)
  );
  waitData.value = res.filter(
    (item) => item.status === 'waiting'
  );
  finishData.value = res.filter(item => item.result);
};

const getData = () => {
  axios
    .get('/v1/job')
    .then((res) => {
      if (!res.error_mesg) {
        devideData(changeTimeFormat(res));
      } else {
        window.$message?.error('无法获取数据，请检查网络连接或联系管理员处理');
      }
    })
    .catch(() => window.$message?.error('发生未知错误，请联系管理员处理'));
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
  getData,
};
