import { ref } from 'vue';
import { get } from '@/assets/CRUD/read';

const data = ref([]);
const loading = ref(false);

const columns = [
  {
    title: '里程碑名',
    key: 'name',
    className: 'cols',
  },
  {
    title: '开始时间',
    key: 'start_time',
    className: 'cols',
  },
  {
    title: '结束时间',
    key: 'end_time',
    className: 'cols',
  },
  {
    title: '任务数',
    key: 'task_num',
    className: 'cols',
  },
];

const getData = (id) => {
  get.filter('/v1/milestone/preciseget', data, loading, { product_id: id });
};

export default {
  data,
  loading,
  columns,
  getData,
};
