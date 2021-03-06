import { h, ref } from 'vue';
import { NTag } from 'naive-ui';
import { SyncCircle, CheckmarkCircle, ArrowForwardCircle } from '@vicons/ionicons5';
import { MdCloseCircleOutline } from '@vicons/ionicons4';
import { IncompleteCircleRound, PauseCircleFilled } from '@vicons/material';
import { any2standard, any2stamp } from '@/assets/utils/dateFormatUtils';
import IssueState from '@/components/public/IssueState.vue';
import { getStatics } from './chart.js';

const issueStateDict = {
  '修复中': {
    color: 'rgba(74,144,226)',
    size: 24,
    icon: IncompleteCircleRound,
  },
  '待办的': {
    color: 'rgba(254,115,0)',
    size: 24,
    icon: SyncCircle,
  },
  '已验收': {
    color: 'green',
    size: 24,
    icon: CheckmarkCircle,
  },
  '已完成': {
    color: 'rgb(140, 146, 164)',
    size: 24,
    icon: CheckmarkCircle,
  },
  '已挂起': {
    color: 'rgb(100, 138, 141)',
    size: 24,
    icon: PauseCircleFilled,
  },
  '已取消': {
    color: 'red',
    size: 24,
    icon: MdCloseCircleOutline,
  },
  '已确认': {
    color: 'yellow',
    size: 24,
    icon: ArrowForwardCircle,
  },
};
const tableData = ref([]);

const columns = [
  {
    title: '状态',
    key: 'issue_state',
    className: 'cols issueState',
    render: (row) => {
      return issueStateDict[row.issue_state]?h(
        IssueState,
        {
          color: issueStateDict[row.issue_state].color,
          size: issueStateDict[row.issue_state].size,
          tip: row.issue_state,
        },
        h(issueStateDict[row.issue_state].icon, null)
      ) : row.issue_state;
    },
    filterOptions: [
      {
        label: '修复中',
        value: '修复中'
      },
      {
        label: '待办的',
        value: '待办的'
      },
      {
        label: '已验收',
        value: '已验收'
      },
      {
        label: '已挂起',
        value: '已挂起'
      },
      {
        label: '已确认',
        value: '已确认'
      },
      {
        label: '已完成',
        value: '已完成'
      },
      {
        label: '已取消',
        value: '已取消'
      },
    ],
    filter (value, row) {
      return ~row.issue_state.indexOf(value);
    }
  },
  {
    title: '编号',
    key: 'id',
    className: 'cols issueNumber',
    render: (row) => {
      return h(
        NTag,
        {
          bordered: false,
          color: {
            color: 'rgba(245,246,248,1)',
            textColor: 'rgba(150,161,175,1)',
          },
        },
        `#${row.id}`
      );
    },
  },
  {
    title: 'issue标题',
    key: 'title',
    className: 'cols issueTitle',
  },
  {
    title: '',
    key: 'priority',
    render: (row) => {
      if (row.priority === 0 || row.priority === 1) {
        return h(
          NTag,
          {
            color: {
              textColor: 'rgba(72,168,68,1)',
              borderColor: 'rgba(72,168,68,1)',
            },
          },
          row.priority === 0 ? '不指定' :'不重要'
        );
      } else if (row.priority === 2) {
        return h(
          NTag,
          {
            color: {
              textColor: 'rgba(0,138,255,1)',
              borderColor: 'rgba(0,138,255,1)',
            },
          },
          '次要'
        );
      } else if (row.priority === 3) {
        return h(
          NTag,
          {
            color: {
              textColor: 'rgba(255,143,0,1)',
              borderColor: 'rgba(255,143,0,1)',
            },
          },
          '主要'
        );
      }
      return h(
        NTag,
        {
          color: {
            textColor: 'rgba(239,0,22,1)',
            borderColor: 'rgba(239,0,22,1)',
          },
        },
        '严重'
      );
    },
  },
  {
    title: '类型',
    key: 'issue_type',
    className: 'cols',
  },
  {
    title: '责任人',
    key: 'assignee.name',
    className: 'cols',
    render: (row) => {
      if (row.assignee?.name) {
        return h('p', null, row.assignee.name);
      }
      return h('p', null, '无责任人');
    },
  },
  {
    title: '创建时间',
    key: 'created_at',
    className: 'cols',
    render: (row) => {
      if (row.created_at) {
        return h('p', null, any2standard(row.created_at));
      }
      return h('p', null, '');
    },
    sorter: (row1, row2) => any2stamp(row1.created_at) - any2stamp(row2.created_at)
  },
  {
    title: '更新时间',
    key: 'updated_at',
    className: 'cols',
    render: (row) => {
      if (row.updated_at) {
        return h('p', null, any2standard(row.updated_at));
      }
      return h('p', null, '');
    },
    sorter: (row1, row2) => any2stamp(row1.updated_at) - any2stamp(row2.updated_at)
  },
];
let tempTableData;
function setTableDate (data) {
  tableData.value = data;
  tempTableData = data;
}
const pagination = ref({
  page: 1,
  pageSize: 10,
  pageSizes: [5, 10, 20, 50],
  showSizePicker: true,
});
function handleFiltersChange (value) {
  if (value.issue_state.length) {
    tableData.value = tempTableData.filter(item => {
      return value.issue_state.includes(item.issue_state);
    });
  } else {
    tableData.value = tempTableData;
  }
}
function changePage(page) {
  pagination.value.page = page;
  getStatics();
}
function changePageSize(pageSize) {
  pagination.value.page = 1;
  pagination.value.pageSize = pageSize;
  getStatics();
}
export { columns, tableData, pagination, setTableDate, handleFiltersChange, changePage, changePageSize };
