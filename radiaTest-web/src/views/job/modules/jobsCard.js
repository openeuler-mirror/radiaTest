import { cols } from '@/views/job/modules';

const initColumns = (columns, type) => {
  if (type === 'execute') {
    columns.value = cols.executeColumns;
  } else if (type === 'wait') {
    columns.value = cols.waitColumns;
  } else {
    columns.value = cols.finishColumns;
  }
};

const initSuffix = (suffix, type) => {
  if (type === 'execute') {
    suffix.value = '正在执行';
  } else if (type === 'wait') {
    suffix.value = '正在等待';
  } else {
    suffix.value = '已完成';
  }
};

export default {
  initColumns,
  initSuffix,
};
