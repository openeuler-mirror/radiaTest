import { describe, expect, it } from 'vitest';

import { PAGE_SIZE } from '#/api';

import { tablePagination } from './table-pagination';

describe('tablePagination', () => {
  it('uses the fixed server-side page size without a size selector', () => {
    expect(tablePagination(3, 123)).toEqual({
      current: 3,
      pageSize: PAGE_SIZE,
      showSizeChanger: false,
      total: 123,
    });
  });
});
