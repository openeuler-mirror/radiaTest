/* eslint-disable max-lines-per-function */
/* eslint-disable indent */
import { h, ref } from 'vue';
import { NIcon, NButton, NTag, NSpace, NPopselect } from 'naive-ui';
import { Construct } from '@vicons/ionicons5';
import { renderTooltip } from '@/assets/render/tooltip';
import { Delete24Regular as Delete } from '@vicons/fluent';
// import { PlugDisconnected20Filled, Connector20Filled } from '@vicons/fluent';
import { Link, Unlink } from '@vicons/carbon';
import axios from '@/axios';
import milestoneTable from '@/views/versionManagement/milestone/modules/milestoneTable.js';
import textDialog from '@/assets/utils/dialog';

const showSyncRepoModal = ref(false);
const selectMilestoneValue = ref('');
const selectMilestoneOptions = ref([]);
const milestoneId = ref(null);

const searchMilestoneFn = (data) => {
  axios
    .get('/v2/gitee-milestone', {
      search: data.name
    })
    .then((res) => {
      selectMilestoneOptions.value = [];
      res.data.data.forEach((v) => {
        selectMilestoneOptions.value.push({
          label: v.title,
          value: v.id
        });
      });
      milestoneId.value = data.id;
    });
};

const syncMilestoneFn = () => {
  axios
    .put(`/v2/milestone/${milestoneId.value}/sync`, {
      gitee_milestone_id: selectMilestoneValue.value
    })
    .then(() => {
      showSyncRepoModal.value = false;
    });
};

const changeState = (data) => {
  axios
    .put(`/v2/milestone/${data.row.id}/state`, {
      state_event: data.value
    })
    .then(() => {
      milestoneTable.getTableData();
    });
};

const deleteMilestone = (data) => {
  axios.delete(`/v2/milestone/${data}`).then(() => {
    milestoneTable.getTableData();
  });
};

const leaveSyncRepoModal = () => {
  selectMilestoneValue.value = '';
  milestoneId.value = null;
};

const constColumns = [
  {
    title: '',
    key: 'is_sync',
    render(row) {
      let [text, icon] = [];
      if (row.is_sync) {
        text = '已与企业仓同步';
        icon = Link;
      } else {
        text = '';
        icon = Unlink;
      }
      return row.is_sync
        ? renderTooltip(
            h(
              NButton,
              {
                size: 'medium',
                type: row.is_sync ? 'primary' : '',
                circle: true,
                onClick: (e) => {
                  e.preventDefault();
                  e.stopPropagation();
                }
              },
              h(NIcon, { size: '20' }, h(icon))
            ),
            text
          )
        : h(
            NButton,
            {
              size: 'medium',
              type: row.is_sync ? 'primary' : '',
              circle: true,
              onClick: (e) => {
                e.preventDefault();
                e.stopPropagation();
                showSyncRepoModal.value = true;
                searchMilestoneFn(row);
              }
            },
            h(NIcon, { size: '20' }, h(icon))
          );
    }
  },
  {
    title: '产品名',
    align: 'center',
    key: 'product_name',
    className: 'cols product-name'
  },
  {
    title: '版本名',
    align: 'center',
    key: 'product_version',
    className: 'cols version-management'
  },
  {
    title: '里程碑名',
    key: 'name',
    className: 'cols milestone-name'
  },
  {
    title: '里程碑类型',
    align: 'center',
    key: 'type',
    className: 'cols milestone-type'
  },
  {
    title: '状态',
    align: 'center',
    key: 'state',
    render(row) {
      return h(
        NPopselect,
        {
          trigger: 'click',
          options: [
            {
              label: 'active',
              value: 'activate'
            },
            {
              label: 'closed',
              value: 'close'
            }
          ],
          'on-update:value': (value) => {
            changeState({ row, value });
          }
        },
        [
          h(
            NButton,
            {
              text: true,
              type: row.state === 'active' ? 'info' : 'error',
              onClick: (e) => {
                e.preventDefault();
                e.stopPropagation();
              }
            },
            row.state
          )
        ]
      );
    }
  },
  {
    title: '开始时间',
    align: 'center',
    key: 'start_time',
    className: 'cols start-time'
  },
  {
    title: '结束时间',
    align: 'center',
    key: 'end_time',
    className: 'cols end-time'
  },
  {
    title: '任务数',
    align: 'center',
    key: 'task_num',
    className: 'cols task'
  }
];

const createColumns = (handler) => {
  return [
    ...constColumns,
    {
      title: '镜像标签',
      key: 'tags',
      align: 'center',
      className: 'cols tags',
      render: (row) => {
        if (row.tags) {
          const hTags = row.tags.map((item) => {
            return h(
              NTag,
              {
                type: 'success'
              },
              item
            );
          });
          return h(NSpace, { justify: 'center' }, hTags);
        }
        return h();
      }
    },
    {
      title: '操作',
      key: 'action',
      className: 'cols operation',
      align: 'center',
      render: (row) => {
        return h(
          NSpace,
          {
            justify: 'center',
            align: 'center'
          },
          [
            renderTooltip(
              h(
                NButton,
                {
                  size: 'medium',
                  type: 'warning',
                  circle: true,
                  onClick: () => handler(row)
                },
                h(NIcon, { size: '20' }, h(Construct))
              ),
              '修改'
            ),
            renderTooltip(
              h(
                NButton,
                {
                  size: 'medium',
                  type: 'error',
                  circle: true,
                  onClick: (e) => {
                    e.preventDefault();
                    e.stopPropagation();
                    textDialog('warning', '警告', '确认删除里程碑？', () => {
                      deleteMilestone(row.id);
                    });
                  }
                },
                h(NIcon, { size: '20' }, h(Delete))
              ),
              '删除'
            )
          ]
        );
      }
    }
  ];
};

export default {
  createColumns,
  showSyncRepoModal,
  selectMilestoneValue,
  selectMilestoneOptions,
  syncMilestoneFn,
  leaveSyncRepoModal
};
