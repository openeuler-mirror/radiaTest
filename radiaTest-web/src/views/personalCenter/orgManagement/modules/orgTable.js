import { h, ref } from 'vue';
import { NAvatar } from 'naive-ui';
import claAndEnterprise from '@/components/orgManagement/claAndEnterprise.vue';

import axios from '@/axios';

const orgs = ref([]);
function getData() {
  axios.get('/v1/admin/org').then((res) => {
    orgs.value = res.data;
    console.log(res, 123);
  });
}

const orgColumns = [
  {
    type: 'expand',
    expandable: (rowData) => rowData.organization_name,
    renderExpand: (rowData) => {
      return h(claAndEnterprise, { info: rowData });
    },
  },
  {
    title: '',
    key: 'organization_avatar',
    align: 'center',
    render(row) {
      return h(NAvatar, {
        size: 'small',
        src: row.organization_avatar,
        style: { background: 'rgba(0,0,0,0)' },
      });
    },
  },
  {
    title: '组织名称',
    key: 'organization_name',
    align: 'center',
  },
  {
    title: '描述',
    key: 'organization_description',
    align: 'center',
  },
];
const pagination = {
  pagesize: 7,
};

export { orgs, pagination, orgColumns, getData };
