import { ref } from 'vue';
const tableData = ref([
  {
    name: 'openEuler',
    public_time: '2022-5-22',
    start_time: '2022-5-20',
    end_time: '2022-5-21',
    bequeath: 'bcf007',
    version: '20',
  },
]);

const columns = [
  {
    key: 'name',
    title: '产品',
    align: 'center'
  },
  {
    key: 'version',
    align: 'center',
    title: '版本'
  },
  {
    key: 'start_time',
    align: 'center',
    title: '开始时间'
  },
  {
    key: 'end_time',
    align: 'center',
    title: '结束时间'
  },
  {
    key: 'public_time',
    align: 'center',
    title: '发布时间'
  },
  {
    key: 'bequeath',
    align: 'center',
    title: '遗留解决'
  }
];

export {
  columns,
  tableData
};
