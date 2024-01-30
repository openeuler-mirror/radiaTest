import { ref } from 'vue';

import axios from '@/axios';
import { changeLoadingStatus } from '@/assets/utils/loading';

const orgList = ref([]);

function getClaOrg() {
  changeLoadingStatus(true);
  orgList.value = [];
  axios
    .get('/v1/org/cla')
    .then((res) => {
      changeLoadingStatus(false);
      if (res?.data && Array.isArray(res.data)) {
        res.data.forEach((element) => {
          orgList.value.push({
            label: element.organization_name,
            value: String(element.organization_id),
            jumpUrl: element.cla_sign_url,
          });
        });
      }
    })
    .catch((err) => {
      window.$message.error(err.data.error_msg);
      changeLoadingStatus(false);
    });
}
export { orgList, getClaOrg };
