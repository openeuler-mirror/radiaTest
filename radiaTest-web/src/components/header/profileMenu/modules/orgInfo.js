import { ref } from 'vue';

import axios from '@/axios';
import { storage } from '@/assets/utils/storageUtils';

const accountName = ref('');
const orgOptions = ref([]);
const currentOrg = ref('');
const activeOrg = ref('');
const avatarUrl = ref('');
function getOrg() {
  axios.get(`/v1/users/${storage.getValue('gitee_id')}`).then((res) => {
    const { data } = res;
    accountName.value = data.gitee_name;
    orgOptions.value = data.orgs.map((item) => {
      return {
        label: item.org_name,
        value: item.org_id
      };
    });
    const defaultOrg = data.orgs.find((item) => {
      return item.re_user_org_default === true;
    });
    activeOrg.value = defaultOrg.org_id;
    currentOrg.value = defaultOrg.org_name;
    storage.setValue('role', defaultOrg.re_user_org_role_type);
    // storage.setValue('orgId', defaultOrg.org_id);
    storage.setValue('gitee_name', data.gitee_name);
    storage.setValue('enterpriseId', defaultOrg.org_enterprise);
    avatarUrl.value = data.avatar_url;
  });
}

export { avatarUrl, currentOrg, activeOrg, accountName, orgOptions, getOrg };
