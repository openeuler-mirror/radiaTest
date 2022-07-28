import { ref } from 'vue';
import store from '@/store';

const filterRule = ref([
  {
    path: 'name',
    name: '产品名称',
    type: 'input'
  },
  {
    path: 'version',
    name: '版本名称',
    type: 'input'
  },
  {
    path: 'description',
    name: '描述',
    type: 'input',
  },
  {
    path: 'start_time',
    name: '开始时间',
    type: 'startdate',
  },
  {
    path: 'end_time',
    name: '结束时间',
    type: 'enddate',
  },
  {
    path: 'public_time',
    name: '发布时间',
    type: 'enddate',
  }
]);

const storeObj = ref({
  name: '',
  version: '',
  description: '',
  start_time: '',
  end_time: '',
  publish_time: ''
});

const filterchange = (filterArray) => {
  storeObj.value = { 
    name: '', 
    version: '', 
    description: '',
    start_time: '',
    end_time: '',
    publish_time: ''
  };
  filterArray.forEach((v) => {
    storeObj.value[v.path] = v.value;
  });
  store.commit('filterProduct/setName', storeObj.value.name);
  store.commit('filterProduct/setVersion', storeObj.value.version);
  store.commit('filterProduct/setDescription', storeObj.value.description);
  store.commit('filterProduct/setStartTime', storeObj.value.start_time);
  store.commit('filterProduct/setEndTime', storeObj.value.end_time);
  store.commit('filterProduct/setPublishTime', storeObj.value.publish_time);
};

const productList = ref([]);
const searchInfo = ref('');
export {
  productList,
  searchInfo,
  filterRule,
  filterchange,
};
