import { ref } from 'vue';
import axios from '@/axios';
import { any2standard } from '@/assets/utils/dateFormatUtils';

const createModalRef = ref(null);
const createFormRef = ref(null);
const copyButton = ref(null);
const createButton = ref(null);

const personalData = ref([]);
const teamData = ref([]);
const orgnizationData = ref([]);
const taskData = ref([]);

const handleHover = (button) => {
  button.style.cursor = 'pointer';
  button.style.color = 'grey';
};
const handleLeave = (button) => {
  button.style.color = 'rgba(206, 206, 206, 1)';
};

const devideData = (res) => {
  try {
    res.forEach((item) => {
      item.create_time
        ? (item.create_time = any2standard(item.create_time))
        : 0;
      item.update_time
        ? (item.update_time = any2standard(item.update_time))
        : 0;
    });
    personalData.value = res.filter(
      (item) => item.template_type === 'personal'
    );
    teamData.value = res.filter((item) => item.template_type === 'team');
    orgnizationData.value = res.filter(
      (item) => item.template_type === 'orgnization'
    );
    taskData.value = res.filter((item) => item.template_type === 'task');
  } catch (error) {
    window.$message?.error(error);
  }
};

const getData = () => {
  axios
    .get('/v1/template')
    .then((res) => {
      devideData(res.data);
    })
    .catch(() => window.$message?.error('发生未知错误，请联系管理员处理'));
};

export default {
  createModalRef,
  createFormRef,
  copyButton,
  createButton,
  personalData,
  teamData,
  orgnizationData,
  taskData,
  handleHover,
  handleLeave,
  devideData,
  getData,
};
