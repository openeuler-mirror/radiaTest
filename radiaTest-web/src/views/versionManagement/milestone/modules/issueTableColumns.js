import { h } from 'vue';
import { NTag } from 'naive-ui';
import { SyncCircle, CheckmarkCircle, ArrowForwardCircle } from '@vicons/ionicons5';
import { MdCloseCircleOutline } from '@vicons/ionicons4';
import { IncompleteCircleRound, PauseCircleFilled } from '@vicons/material';
import { any2standard, any2stamp } from '@/assets/utils/dateFormatUtils';
import IssueState from '@/components/public/IssueState.vue';

export const issueStateDict = {
  修复中: {
    color: 'rgba(74,144,226)',
    size: 24,
    icon: IncompleteCircleRound
  },
  待办的: {
    color: 'rgba(254,115,0)',
    size: 24,
    icon: SyncCircle
  },
  已验收: {
    color: 'green',
    size: 24,
    icon: CheckmarkCircle
  },
  已完成: {
    color: 'rgb(140, 146, 164)',
    size: 24,
    icon: CheckmarkCircle
  },
  已挂起: {
    color: 'rgb(100, 138, 141)',
    size: 24,
    icon: PauseCircleFilled
  },
  已取消: {
    color: 'red',
    size: 24,
    icon: MdCloseCircleOutline
  },
  已确认: {
    color: 'yellow',
    size: 24,
    icon: ArrowForwardCircle
  }
};

const columns = [
  {
    title: '状态',
    key: 'issue_state',
    className: 'cols issueState',
    render: (row) => {
      return h(
        IssueState,
        {
          color: row.issue_state.color,
          size: issueStateDict[row.issue_state.title]?.size || 24,
          tip: row.issue_state.title
        },
        h(issueStateDict[row.issue_state.title]?.icon || SyncCircle, null)
      );
    }

  },
  {
    title: '编号',
    key: 'ident',
    className: 'cols issueNumber',
    render: (row) => {
      return h(
        NTag,
        {
          bordered: false,
          color: {
            color: 'rgba(245,246,248,1)',
            textColor: 'rgba(150,161,175,1)'
          }
        },
        `#${row.ident}`
      );
    }
  },
  {
    title: 'issue标题',
    key: 'title',
    className: 'cols issueTitle'
  },
  {
    title: '优先级',
    key: 'priority',
    render: (row) => {
      if (row.priority === 1) {
        return h(
          NTag,
          {
            color: {
              textColor: 'rgba(72,168,68,1)',
              borderColor: 'rgba(72,168,68,1)'
            }
          },
          '可选'
        );
      } else if (row.priority === 2) {
        return h(
          NTag,
          {
            color: {
              textColor: 'rgba(0,138,255,1)',
              borderColor: 'rgba(0,138,255,1)'
            }
          },
          '次要'
        );
      } else if (row.priority === 3) {
        return h(
          NTag,
          {
            color: {
              textColor: 'rgba(255,143,0,1)',
              borderColor: 'rgba(255,143,0,1)'
            }
          },
          '主要'
        );
      } else if (row.priority === 4) {
        return h(
          NTag,
          {
            color: {
              textColor: 'rgba(239,0,22,1)',
              borderColor: 'rgba(239,0,22,1)'
            }
          },
          '严重'
        );
      }
      return '';
    }
  },
  {
    title: '责任人',
    key: 'name',
    className: 'cols',
    render: (row) => {
      if (row.assignee) {
        return h('p', null, row.assignee.name);
      }
      return h('p', null, '无责任人');
    }
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
  }
];
export default columns;
