import { reactive } from 'vue';

const pagination = reactive({
  pageSize: 10,
  showSizePicker: true,
  pageSizes: [5, 10, 20, 50, 100],
  onChange: (page) => {
    pagination.page = page;
  },
  onPageSizeChange: (pageSize) => {
    (pagination.pageSize = pageSize), (pagination.page = 1);
  },
});

export default {
  pagination,
};
