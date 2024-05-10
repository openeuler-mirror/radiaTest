import axios from '@/axios';
import { NPopover, NTag } from 'naive-ui';
import { h, ref } from 'vue';
import { formatTime, timeProcess } from '@/assets/utils/dateFormatUtils';

const loading = ref(false);
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
      return timeProcess(row.running_time, 'ms');
    },
  },
  {
    title: '状态',
    key: 'status',
    align: 'center',
    render: (row) => {
      let color = '';
      if (row.status === 'SUCCESS') {
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

];
const taskData = ref([]);
const pagination = ref({
  page: 1,
  pageCount: 1,
  pageSize: 10,
  showSizePicker: true,
  pageSizes: [5, 10, 20],
});
const searchInfo = ref();
function getTask() {
  loading.value = true;
  axios
    .get('/v1/celerytask', {
      page_num: pagination.value.page,
      page_size: pagination.value.pageSize,
      tid: searchInfo.value,
    })
    .then((res) => {
      loading.value = false;
      taskData.value = res.data.items?.map((item) => item);
      pagination.value.pageCount = res.data.pages;
    }).catch(err => {
      loading.value = false;
      window.$message?.error(err.data.error_msg || '未知错误');
    });
}
function handlePageChange(page) {
  pagination.value.page = page;
  getTask();
}
function handlePageSizeChange(pageSize) {
  pagination.value.pageSize = pageSize;
  pagination.value.page = 1;
  getTask();
}

function searchTask() {
  pagination.value.page = 1;
  getTask();
}
export {
  searchInfo,
  taskData,
  taskColumns,
  pagination,
  getTask,
  handlePageChange,
  handlePageSizeChange,
  searchTask,
};
