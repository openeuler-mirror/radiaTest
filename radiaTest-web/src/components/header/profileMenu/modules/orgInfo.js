import { ref } from 'vue';

// import axios from '@/axios';
import { storage } from '@/assets/utils/storageUtils';
import { getAllOrg, getUserInfo } from '@/api/get';
const accountName = ref('');
const orgOptions = ref([]);
const currentOrg = ref('');
const activeOrg = ref('');
const avatarUrl = ref('');
function getOrg() {
  getUserInfo(storage.getValue('user_id')).then((res) => {
    const { data } = res;
    accountName.value = data.user_name;
    orgOptions.value = data.orgs.map((item) => {
      return {
        label: item.org_name,
        value: item.org_id
      };
    });
    const defaultOrg = data?.orgs?.find((item) => {
      return item.re_user_org_default === true;
    });
    activeOrg.value = defaultOrg?.org_id;
    currentOrg.value = defaultOrg?.org_name;
    storage.setValue('role', defaultOrg?.re_user_org_role_type);
    // storage.setValue('orgId', defaultOrg.org_id);
    storage.setValue('user_name', data?.user_name);
    storage.setValue('enterpriseId', defaultOrg?.org_enterprise);
    avatarUrl.value = data?.avatar_url;
  });
}
const selectedOrg = ref('');
const orgListoptions = ref([]);
function getOrgList() {
  getAllOrg().then((res) => {
    orgListoptions.value = res.data.map((item) => ({
      label: item.org_name,
      value: { name: item.org_name, id: String(item.org_id) },
      ...item
    }));
  }).then(() => {
    if (storage.getLocalValue('unLoginOrgId')) {
      selectedOrg.value = storage.getLocalValue('unLoginOrgId');
    } else if (!storage.getLocalValue('unLoginOrgId') && orgListoptions.value.some(obj => obj.label === 'openEuler')) {
      selectedOrg.value = (orgListoptions.value.find(obj => obj.label === 'openEuler')).value;
      storage.setLocalValue('unLoginOrgId', selectedOrg.value);
    }
  });
}


export { avatarUrl, currentOrg, activeOrg, accountName, orgOptions, getOrg, selectedOrg, orgListoptions, getOrgList };
