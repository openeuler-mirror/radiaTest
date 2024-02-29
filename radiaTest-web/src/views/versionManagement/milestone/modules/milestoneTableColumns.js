/* eslint-disable max-lines-per-function */
/* eslint-disable indent */
import { h, ref } from 'vue';
import { NIcon, NButton, NSpace, NPopselect } from 'naive-ui';
import { Construct } from '@vicons/ionicons5';
import { renderTooltip } from '@/assets/render/tooltip';
import { Delete24Regular as Delete } from '@vicons/fluent';
import { Link, Unlink } from '@vicons/carbon';
import milestoneTable from '@/views/versionManagement/milestone/modules/milestoneTable.js';
import textDialog from '@/assets/utils/dialog';
import { getMilestonesByName } from '@/api/get';
import { updateSyncMilestone, updateMilestoneState } from '@/api/put';
import { deleteMilestoneAjax } from '@/api/delete';

const showSyncRepoModal = ref(false);
const selectMilestoneValue = ref('');
const selectMilestoneOptions = ref([]);
const milestoneId = ref(null);
const loading = ref(false);
const searchName = ref({});
const page = ref(1);
const hasNext = ref(true);
const perPage = 30;
const searchMilestoneFn = () => {
  loading.value = true;
  getMilestonesByName({
    search: searchName.value.name,
    per_page: perPage,
    page: page.value,
  }).then((res) => {
    milestoneId.value = searchName.value.id;
    hasNext.value = res.data.has_next;
    res.data.data.forEach(item => {
      item.label = item.title;
      item.value = item.id;
    });
    selectMilestoneOptions.value = selectMilestoneOptions.value.concat(res.data.data);
    loading.value = false;
  });
};
const syncMilestoneFn = () => {
  updateSyncMilestone(milestoneId.value, {
    gitee_milestone_id: selectMilestoneValue.value
  }).then(() => {
    showSyncRepoModal.value = false;
  }).catch(() => {
    showSyncRepoModal.value = false;
  });
};

const handleScroll = async (e) => {
  const currentTarget = e.currentTarget;
  if (currentTarget.scrollTop + currentTarget.offsetHeight >= currentTarget.scrollHeight) {
    if (hasNext.value) {
      page.value = page.value + 1;
      searchMilestoneFn();
    }
  }
};

const changeState = (data) => {
  updateMilestoneState(data.row.id, {
    state_event: data.value
  }).then(() => {
    milestoneTable.getTableData();
  });
};

const deleteMilestone = (data) => {
  deleteMilestoneAjax(data).then(() => {
    milestoneTable.getTableData();
  });
};

const leaveSyncRepoModal = () => {
  selectMilestoneValue.value = '';
  milestoneId.value = null;
};

const startTimeColumn = reactive({
  title: '开始时间',
  align: 'center',
  key: 'start_time',
  className: 'cols start-time',
  sorter: true,
  sortOrder: false
});

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
              searchName.value = row;
              searchMilestoneFn();
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
  startTimeColumn,
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
  leaveSyncRepoModal,
  startTimeColumn,
  handleScroll
};
