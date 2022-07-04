import { ref } from 'vue';

const codeTableLoading = ref(false);
const codePagination = ref(false);
const codeData = ref([]);
const keyword = ref('');
import axios from '@/axios';
import router from '@/router';

const codeColumns = [
  {
    title: '仓库名称',
    key: 'name'
  },
  {
    title: '所属框架',
    key: 'frameworkName'
  },
  {
    title: '代码仓地址',
    key: 'git_url'
  },
  {
    title: '同步策略',
    key: 'syncRule'
  },
  {
    title: '解析适配',
    key: 'isAdapt'
  },
];

function getCodeData() {
  const id  = parseInt(router.currentRoute.value.query.id);
  const url = 'v1/git-repo';
  axios.get(url,{
    group_id: id,
    query_item: keyword.value
  }).then(res => {
    res.data?.map(item => {
      item.frameworkName = item.framework.name;
      item.syncRule = item.sync_rule ? '是' : '否';
      item.isAdapt = item.is_adapt ? '是' : '否';
    });
    codeData.value = res.data;
  });
}

export{
  codeTableLoading,
  codePagination,
  codeColumns,
  codeData,
  keyword,
  getCodeData
};
