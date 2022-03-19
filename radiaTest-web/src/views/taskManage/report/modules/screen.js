import { ref, h } from 'vue';
import { NAvatar } from 'naive-ui';

import axios from '@/axios';
import { storage } from '@/assets/utils/storageUtils';

const weekMS = 1000 * 60 * 60 * 24 * 7;
const timeRange = ref([Date.now() - weekMS, Date.now()]);

const type = ref('');
const typeOptions = [
  { label: '个人任务', value: 'PERSON' },
  { label: '团队任务', value: 'GROUP' },
  { label: '组织任务', value: 'ORGANIZATION' },
  { label: '版本任务', value: 'VERSION' },
];

const owner = ref([]);
const ownerOptions = ref([]);

const milestone = ref('');
const milestoneOptions = ref([]);
function disablePreviousDate(ts) {
  return ts > Date.now();
}

function getMilestone () {
  axios.get('/v2/milestone').then(res => {
    milestoneOptions.value = [];
    for (const item of res) {
      milestoneOptions.value.push({
        value: item.id,
        label: item.name,
      });
    }
  });
}

function getOwner() {
  const requests = [];
  requests.push(axios.get(`/v1/org/${storage.getValue('orgId')}/users`, { page_size: 99999, page_num: 1, }));
  ownerOptions.value = [];
  Promise.allSettled(requests).then(responses => {
    responses.forEach(item => {
      if (item.value?.data?.items) {
        for (const i of item.value.data.items) {
          const element = {
            value: i.id ? i.id : i.gitee_id,
            avatar: i.avatar_url,
            label: i.name ? i.name : i.gitee_name,
          };
          ownerOptions.value.push(element);
        }
      }
    });
  });
}
function renderLabel(option) {
  return h(
    'div',
    {
      style: {
        display: 'flex',
        alignItems: 'center'
      }
    },
    [
      h(NAvatar, {
        src: option.avatar,
        round: true,
        size: 'small'
      }),
      option.label
    ]
  );
}
export {
  type,
  milestone,
  milestoneOptions,
  owner,
  timeRange,
  typeOptions,
  ownerOptions,
  getOwner,
  getMilestone,
  renderLabel,
  disablePreviousDate,
};
