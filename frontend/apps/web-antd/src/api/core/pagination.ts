export const PAGE_SIZE = 50;

export interface PageParams {
  page?: number;
}

export interface PaginatedResponse<T> {
  items: T[];
  page: number;
  page_size: number;
  total: number;
}
