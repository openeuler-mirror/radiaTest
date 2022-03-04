import axios from '@/axios';
import { NPopover, NProgress, NTag } from 'naive-ui';
import { h, ref } from 'vue';
import { formatTime } from '@/assets/utils/dateFormatUtils';

const loading = ref(false);
function detailNumber(num) {
  const str = String(num);
  const [I, F] = str.split('.');
  let result = I;
  if (F) {
    I.length > 3
      ? (result = `${result}.${F.slice(0, 2)}`)
      : (result = `${result}.${F.slice(0, 4)}`);
  }
  return result;
}
const taskColumns = [
  { title: '任务ID', key: 'tid', align: 'center' },
  {
    title: '类别',
    key: 'object_type',
    align: 'center',
    render(row) {
      return h(
        NPopover,
        { trigger: 'hover' },
        {
          trigger: row.object_type,
          default: () =>
            h(
              'span',
              row.object_type === 'vmachine' || row.object_type === 'pmachine'
                ? row.machine.description
                : row.description
            ),
        }
      );
    },
  },
  {
    title: '开始时间',
    key: 'start_time',
    align: 'center',
    render(row) {
      return formatTime(row.start_time, 'yyyy-MM-dd hh:mm:ss');
    },
  },
  {
    title: '已执行时间',
    key: 'running_time',
    align: 'center',
    render(row) {
      if (row.running_time > 1000 * 1000) {
        return `${detailNumber(row.running_time / (1000 * 1000))}s`;
      }
      return row.running_time ? `${detailNumber(row.running_time / 1000)}ms` : '';
    },
  },
  {
    title: '状态',
    key: 'status',
    align: 'center',
    render: (row) => {
      let color = 'grey';
      if (row.status === 'DONE') {
        color = 'success';
      } else if (row.status === 'FAILURE') {
        color = 'error';
      }
      return h(
        NTag,
        { type: color, round: true, style: 'cursor:pointer' },
        row.status
      );
    },
  },
  {
    title: '预估进度',
    align: 'center',
    width:200,
    render() {
      return h(NProgress, {
        type: 'line',
        processing: true,
        indicatorPlacement: 'inside',
        percentage: 60,
      });
    },
  },
];
const taskData = ref([]);
const pagination = ref({
  page: 1,
  pageCount: 1,
  pageSize: 10,
  showSizePicker: true,
  pageSizes: [5, 10, 20]
});
function getTask () {
  loading.value = true;
  axios
    .get('/v1/celerytask', {
      page_num: pagination.value.page,
      page_size: pagination.value.pageSize,
    })
    .then((res) => {
      loading.value = false;
      taskData.value = res.data.items?.map((item) => item);
      pagination.value.pageCount = res.data.pages;
    });
}
function handlePageChange(page) {
  pagination.value.page = page;
  getTask();
}
function handlePageSizeChange (pageSize) {
  pagination.value.pageSize = pageSize;
  pagination.value.page = 1;
  console.log(pageSize);
  getTask();
}
export { taskData, taskColumns, pagination, getTask, handlePageChange, handlePageSizeChange };
