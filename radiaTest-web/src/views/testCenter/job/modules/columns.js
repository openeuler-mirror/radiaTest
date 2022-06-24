import { h } from 'vue';
import {
  NTag,
  NIcon,
  NButton,
  NProgress,
  NPopover,
  NGradientText,
} from 'naive-ui';
import { CheckCircle } from '@vicons/fa';
import { CancelFilled } from '@vicons/material';
import { timeProcess } from '@/assets/utils/dateFormatUtils';

import job from './job';

const executeColumns = [
  {
    title: '任务编号',
    key: 'id',
    className: 'cols',
    fixed: 'left',
    width: 100,
  },
  {
    title: '任务名',
    key: 'name',
    fixed: 'left',
    width: 300,
    className: 'cols',
  },
  {
    title: '里程碑',
    key: 'milestone',
    className: 'cols',
  },
  {
    title: '执行机器IP',
    key: 'master',
    className: 'cols',
    render(row) {
      if (row.master?.length) {
        if (Array.isArray(row.master) && row.master.length > 1) {
          return h(
            NPopover,
            {
              trigger: 'hover',
            },
            {
              default: () => {
                return h(
                  'div',
                  row.master.map((item) => {
                    return h('p', item);
                  })
                );
              },
              trigger: () => h(NGradientText, { type: 'info' }, '查看'),
            }
          );
        }
        return Array.isArray(row.master) ? row.master.join(',') : row.master;
      }
      return '尚未分配';
    },
  },
  {
    title: '用例数量',
    key: 'total',
    className: 'cols',
  },
  {
    title: '执行进度',
    key: 'progress',
    className: 'cols progress',
    render: (row) => {
      return h(NProgress, {
        type: 'line',
        percentage: parseInt(
          ((row.success_cases + row.fail_cases) * 100) / row.total
        ),
        indicatorPlacement: 'inside',
        processing: true,
        height: '20px',
      });
    },
  },
  {
    title: '开始时间',
    key: 'start_time',
    className: 'cols',
  },
  {
    title: '当前状态',
    key: 'status',
    fixed: 'right',
    width: 100,
    className: 'cols',
    render: (row) => {
      if(!row.id){
        return '';
      }
      if (row.status === 'testing') {
        return h(
          NTag,
          {
            type: 'success',
            round: true,
          },
          'testing'
        );
      }
      return h(
        NTag,
        {
          type: 'info',
          round: true,
        },
        row.status
      );
    },
  },
];

const waitColumns = [
  {
    title: '任务编号',
    key: 'id',
    className: 'cols',
    fixed: 'left',
    width: 100,
  },
  {
    title: '任务名',
    key: 'name',
    className: 'cols',
    fixed: 'left',
    width: 300,
  },
  {
    title: '创建时间',
    key: 'create_time',
    className: 'cols',
    render(row){
      if (row.create_time) {
        return row.create_time;
      }
      return '尚未分配';
    }
  },
  {
    title: '运行时间',
    key: 'running_time',
    render(row) {
      if(!row.id){
        return '';
      }
      return timeProcess(row.running_time, 'ms');
    },
  },
  {
    title: '里程碑',
    key: 'milestone',
    className: 'cols',
    width: 200,
  },
  {
    title: '用例数量',
    key: 'total',
    className: 'cols',
  },
  {
    title: '当前状态',
    key: 'status',
    fixed: 'right',
    width: 100,
    className: 'cols',
    render: (row) => {
      if(!row.id){
        return '';
      }
      return h(
        NTag,
        {
          type: 'default',
          round: true,
        },
        row.status
      );
    },
  },
];

const finishColumns = [
  {
    title: '任务编号',
    key: 'id',
    className: 'cols',
    fixed: 'left',
    width: 100,
  },
  {
    title: '任务名称',
    key: 'name',
    className: 'cols',
    fixed: 'left',
    width: 300,
  },
  {
    title: '里程碑',
    key: 'milestone',
    className: 'cols',
    width: 200,
  },
  {
    title: '执行机器IP',
    key: 'master',
    className: 'cols',
    render(row) {
      if (row.master?.length) {
        if (Array.isArray(row.master) && row.master.length > 1) {
          return h(
            NPopover,
            {
              trigger: 'hover',
            },
            {
              default: () => {
                return h(
                  'div',
                  row.master.map((item) => {
                    return h('p', item);
                  })
                );
              },
              trigger: () => h(NGradientText, { type: 'info' }, '查看'),
            }
          );
        }
        return Array.isArray(row.master) ? row.master.join(',') : row.master;
      }
      return '尚未分配';
    },
  },
  {
    title: '结束时间',
    key: 'end_time',
    className: 'cols',
  },
  {
    title: '运行时间',
    key: 'running_time',
    render(row) {
      if(!row.id){
        return '';
      }
      return timeProcess(row.running_time, 'ms');
    },
  },
  {
    title: '成功-失败-总数',
    key: 'statistic',
    className: 'cols',
    render: (row) => {
      if(!row.id){
        return '';
      }
      if (row.total) {
        return h('div', {}, [
          h(
            'p',
            { style: { display: 'inline-block' } },
            `${row.success_cases}-`
          ),
          h('p', { style: { display: 'inline-block' } }, `${row.fail_cases}-`),
          h('p', { style: { display: 'inline-block' } }, `${row.total}`),
        ]);
      }
      return null;
    },
  },
  {
    title: '执行日志',
    key: 'log_url',
    fixed: 'right',
    width: 100,
    className: 'cols',
    render: (row) => {
      if(!row.id){
        return '';
      }
      return h(
        NButton,
        {
          onClick: () => {
            if (row.status !== 'BLOCK') {
              job.logsDrawer.value.showDrawer(row);
            } else {
              window.$message?.warning(row.remark || '未知错误');
            }
          },
        },
        '查看'
      );
    },
  },
  {
    title: '执行结果',
    key: 'result',
    className: 'cols',
    fixed: 'right',
    width: 100,
    render: (row) => {
      if(!row.id){
        return '';
      }
      if (row.result === 'success') {
        return h(
          NIcon,
          {
            color: 'green',
            size: '24',
            style: {
              position: 'relative',
              top: '3px',
            },
          },
          h(CheckCircle, {})
        );
      }
      return h(
        NIcon,
        {
          color: 'rgba(206,64,64,1)',
          size: '26',
          style: {
            position: 'relative',
            top: '1px',
          },
        },
        h(CancelFilled, {})
      );
    },
  },
  {
    title: '状态',
    key: 'status',
    className: 'cols',
    fixed: 'right',
    width: 100,
    render: (row) => {
      if(!row.id){
        return '';
      }
      if (row.result === 'success') {
        return h(
          NTag,
          {
            type: 'success',
            round: true,
          },
          row.status
        );
      }
      return h(
        NTag,
        {
          type: 'error',
          round: true,
        },
        row.status
      );
    },
  },
];

export default {
  executeColumns,
  waitColumns,
  finishColumns,
};
