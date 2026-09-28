import type { TablePaginationConfig } from 'ant-design-vue';

import { PAGE_SIZE } from '#/api';

export function tablePagination(
  current: number,
  total: number,
): TablePaginationConfig {
  return {
    current,
    pageSize: PAGE_SIZE,
    showSizeChanger: false,
    total,
  };
}
