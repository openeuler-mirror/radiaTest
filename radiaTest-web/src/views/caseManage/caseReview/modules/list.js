import { ref } from 'vue';
import { getCaseReview } from '@/api/get';
import { errorMessage } from '@/assets/utils/message';
const dataList = ref([]);
const filterOptions = [
  {
    label: '全部',
    value: 'all'
  },
  {
    label: '我创建的',
    value: 'creator'
  }
];
const filter = ref('all');
const searchInfo = ref('');
const activeType = ref('all');
const page = ref(1);
const pageCount = ref(1);
const loading = ref(false);
const types = ref([
  {
    label: '全部',
    value: 'all',
    count: 0
  },
  {
    label: '开启的',
    value: 'open',
    count: 0
  },
  {
    label: '已合并',
    value: 'accepted',
    count: 0
  },
  {
    label: '已关闭',
    value: 'rejected',
    count: 0
  }
]);
let allData;

function setData() {
  dataList.value = allData[`${activeType.value}_commit`]?.items || [];
  types.value[0].count = allData.all_count;
  types.value[1].count = allData.open_count;
  types.value[2].count = allData.accepted_count;
  types.value[3].count = allData.rejected_count;
  pageCount.value = allData[`${activeType.value}_commit`]?.pages || 1;
}

function clickTypeBtn(value) {
  activeType.value = value;
  setData();
}

function getData() {
  loading.value = true;
  getCaseReview({ page_num: page.value, page_size: 10, user_type: filter.value, title: searchInfo.value })
    .then((res) => {
      loading.value = false;
      allData = res.data;
      setData();
    })
    .catch((err) => {
      loading.value = false;
      errorMessage(err);
    });
}
function pageChange(value) {
  page.value = value;
  getData();
}

export {
  dataList,
  filter,
  activeType,
  searchInfo,
  filterOptions,
  types,
  page,
  loading,
  pageCount,
  pageChange,
  getData,
  setData,
  clickTypeBtn
};
